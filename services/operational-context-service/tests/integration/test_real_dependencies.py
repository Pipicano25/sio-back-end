"""Integración real con Keycloak, Party Identity y Geography (FR-075, T073).

Se ejecuta solo con `pytest -m integration` y exige los servicios en ejecución:

- Operational Context en `OPERATIONAL_CONTEXT_INTEGRATION_BASE_URL` (por defecto
  `http://localhost:8004`), configurado contra los mismos Party Identity y Geography;
- Party Identity en `PARTY_IDENTITY_SERVICE_BASE_URL` (con `/api/v1`) y Geography en
  `GEOGRAPHY_SERVICE_BASE_URL`, con las reglas y los datos de Colombia cargados;
- Keycloak en `KEYCLOAK_TOKEN_URL`, con la contraseña de los usuarios de prueba en
  `KEYCLOAK_TEST_USER_PASSWORD` o en `infrastructure/.env` (nunca en el código).

**Repetible**: cada ejecución crea en Party Identity una organización nueva, con datos
**ficticios de validación** (razón social con prefijo `PRUEBA SIO OC <id de ejecución>`) y un
número de identificación único generado en tiempo de ejecución que cumple la regla vigente. No
depende de `DELETE`: la organización, la empresa y la sucursal quedan como datos ficticios de
validación en el entorno y no provocan `409` en ejecuciones posteriores.

Caída de un proveedor (`503`): detenga su contenedor (p. ej. `docker stop sio-geography-service`)
y repita un alta con ubicación; la respuesta es `503 OPERATIONAL_CONTEXT.DEPENDENCY_UNAVAILABLE` y
el log del servicio muestra `GEOGRAPHY_UNAVAILABLE` con el mismo `trace_id` que `X-Trace-Id`.
Se documenta aquí y no se automatiza para no detener servicios compartidos.
"""

from __future__ import annotations

import os
import random
import re
import secrets
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

pytestmark = pytest.mark.integration

REPO_ROOT = Path(__file__).resolve().parents[4]
PASSWORD_VARIABLE = "KEYCLOAK_TEST_USER_PASSWORD"

OPERATIONAL_CONTEXT = os.environ.get("OPERATIONAL_CONTEXT_INTEGRATION_BASE_URL", "http://localhost:8004").rstrip("/")
PARTY_IDENTITY = os.environ.get("PARTY_IDENTITY_SERVICE_BASE_URL", "http://localhost:8002/api/v1").rstrip("/")
GEOGRAPHY = os.environ.get("GEOGRAPHY_SERVICE_BASE_URL", "http://localhost:8000").rstrip("/")
TOKEN_URL = os.environ.get(
    "KEYCLOAK_TOKEN_URL",
    "http://localhost:8081/realms/sio/protocol/openid-connect/token",
)
RUN_ID = secrets.token_hex(4).upper()


def _password() -> str | None:
    value = os.environ.get(PASSWORD_VARIABLE, "").strip()
    env_file = REPO_ROOT / "infrastructure" / ".env"
    if not value and env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            name, separator, content = line.partition("=")
            if separator and name.strip() == PASSWORD_VARIABLE:
                value = content.strip().strip('"').strip("'")
    return value or None


@pytest.fixture(scope="module")
def client():
    password = _password()
    if not password:
        pytest.skip(f"Defina {PASSWORD_VARIABLE} (o infrastructure/.env) para las pruebas de integración.")

    with httpx.Client(timeout=10) as http:
        for url in (f"{OPERATIONAL_CONTEXT}/health/ready", f"{GEOGRAPHY}/health/live"):
            try:
                http.get(url).raise_for_status()
            except httpx.HTTPError:
                pytest.skip(f"Servicio no disponible para integración: {url}")
        try:
            token = http.post(TOKEN_URL, data={
                "grant_type": "password", "client_id": "sio-web", "scope": "openid",
                "username": "admin.test", "password": password,
            }).raise_for_status().json()["access_token"]
        except (httpx.HTTPError, KeyError):
            pytest.skip("No fue posible obtener el token de admin.test en Keycloak.")

        http.headers["Authorization"] = f"Bearer {token}"
        yield http


def _first_id(client, url, **params) -> str:
    response = client.get(url, params=params)
    response.raise_for_status()
    items = response.json()["items"]
    if not items:
        pytest.skip(f"Sin datos en {url} {params}")
    return items[0]["id"]


@pytest.fixture(scope="module")
def geography(client):
    colombia = _first_id(client, f"{GEOGRAPHY}/global-countries", iso3_code="COL")
    antioquia = _first_id(client, f"{GEOGRAPHY}/global-administrative-divisions", country_id=colombia, search="Antioquia")
    cundinamarca = _first_id(
        client, f"{GEOGRAPHY}/global-administrative-divisions", country_id=colombia, search="Cundinamarca",
    )
    medellin = _first_id(client, f"{GEOGRAPHY}/global-cities", administrative_division_id=antioquia, search="Medell")
    return {"colombia": colombia, "antioquia": antioquia, "cundinamarca": cundinamarca, "medellin": medellin}


def _conforming_number(pattern: str) -> str:
    """Genera un número único que cumple el patrón vigente de la regla (sin valores fijos)."""
    regex = re.compile(pattern)
    for _ in range(200):
        base_length = random.randint(8, 10)
        base = str(random.randint(1, 9)) + "".join(random.choice("0123456789") for _ in range(base_length - 1))
        for candidate in (f"{base}-{random.randint(0, 9)}", base):
            if regex.fullmatch(candidate):
                return candidate
    pytest.skip(f"No se pudo generar un número que cumpla el patrón {pattern!r}.")


@pytest.fixture(scope="module")
def organization_id(client, geography):
    """Organización nueva y exclusiva de esta ejecución (datos ficticios de validación)."""
    rules = client.get(
        f"{PARTY_IDENTITY}/identification-type-rules",
        params={"party_kind": "ORGANIZATION", "country_id": geography["colombia"], "sigla": "NIT", "is_active": "true"},
    ).raise_for_status().json()["items"]
    if not rules:
        pytest.skip("Party Identity no tiene la regla NIT activa para Colombia (ejecute su seed).")

    for _ in range(5):
        response = client.post(f"{PARTY_IDENTITY}/organization-identities", json={
            "country_id": geography["colombia"],
            "identification_type": "NIT",
            "identification_number": _conforming_number(rules[0]["number_pattern"]),
            "legal_name": f"PRUEBA SIO OC {RUN_ID} (DATO FICTICIO DE VALIDACION)",
        })
        if response.status_code == 201:
            return response.json()["id"]
        if response.status_code != 409:
            pytest.fail(f"Party Identity respondió {response.status_code}: {response.text}")
    pytest.fail("No se obtuvo un número de identificación libre tras 5 intentos.")


def test_company_and_branch_with_real_dependencies(client, geography, organization_id):
    company = client.post(f"{OPERATIONAL_CONTEXT}/api/v1/companies", json={
        "organization_identity_id": organization_id,
        "email": f"validacion-{RUN_ID.lower()}@empresa-ficticia.co",
        "country_id": geography["colombia"],
        "administrative_division_id": geography["antioquia"],
        "city_id": geography["medellin"],
    })
    assert company.status_code == 201, company.text
    company_id = company.json()["id"]
    assert company.json()["status"] == "ACTIVE"

    branch = client.post(f"{OPERATIONAL_CONTEXT}/api/v1/companies/{company_id}/branches", json={
        "code": f"VAL-{RUN_ID}",
        "name": f"Sucursal ficticia de validación {RUN_ID}",
        "country_id": geography["colombia"],
        "administrative_division_id": geography["antioquia"],
        "city_id": geography["medellin"],
    })
    assert branch.status_code == 201, branch.text
    body = branch.json()
    assert body["company_status"] == "ACTIVE"
    assert body["effective_timezone"] == "America/Bogota"

    provider = client.get(f"{OPERATIONAL_CONTEXT}/api/v1/branches/{body['id']}")
    assert provider.status_code == 200
    assert provider.json()["company_id"] == company_id


def test_real_geography_incoherence_on_branch(client, geography, organization_id):
    companies = client.get(
        f"{OPERATIONAL_CONTEXT}/api/v1/companies", params={"organization_identity_id": organization_id}
    ).json()["items"]
    assert companies, "La prueba anterior debía crear la empresa de esta ejecución."

    response = client.post(f"{OPERATIONAL_CONTEXT}/api/v1/companies/{companies[0]['id']}/branches", json={
        "code": f"INC-{RUN_ID}",
        "name": "Sucursal incoherente (dato ficticio)",
        "country_id": geography["colombia"],
        "administrative_division_id": geography["cundinamarca"],
        "city_id": geography["medellin"],
    })

    assert response.status_code == 422
    assert response.json()["code"] == "OPERATIONAL_CONTEXT.GEOGRAPHY_INCOHERENT"
    assert response.json()["errors"][0]["field"] == "city_id"


def test_real_unknown_organization_is_422(client):
    response = client.post(f"{OPERATIONAL_CONTEXT}/api/v1/companies", json={"organization_identity_id": str(uuid4())})

    assert response.status_code == 422
    assert response.json()["code"] == "OPERATIONAL_CONTEXT.ORGANIZATION_IDENTITY_NOT_FOUND"


# ---------------------------------------------------------------------------
# Fase B (specs/005-operational-context-users, FR-094): Keycloak Admin API de
# solo lectura y personas de Party Identity reales. Exige el realm renderizado
# con el cliente técnico `operational-context-service` y su secreto en el
# entorno del servicio. Cada ejecución crea una persona ficticia de validación.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def person_id(client, geography):
    """Persona nueva y exclusiva de esta ejecución (datos ficticios de validación)."""
    rules = client.get(
        f"{PARTY_IDENTITY}/identification-type-rules",
        params={"party_kind": "PERSON", "country_id": geography["colombia"], "sigla": "CC", "is_active": "true"},
    ).raise_for_status().json()["items"]
    if not rules:
        pytest.skip("Party Identity no tiene la regla CC activa para Colombia (ejecute su seed).")

    for _ in range(5):
        # Número que cumple el patrón vigente de la regla (sin valores fijos), como la organización.
        number = _conforming_number(rules[0]["number_pattern"])
        response = client.post(f"{PARTY_IDENTITY}/person-identities", json={
            "identification_country_id": geography["colombia"],
            "identification_type": "CC",
            "identification_number": number,
            "first_name": f"PRUEBA{RUN_ID}",
            "last_name": "DATO FICTICIO DE VALIDACION",
            "birth_date": "1990-01-01",
        })
        if response.status_code == 201:
            return response.json()["id"]
        if response.status_code != 409:
            pytest.skip(f"Party Identity no aceptó la persona de validación: {response.status_code} {response.text}")
    pytest.fail("No se obtuvo un número de identificación libre tras 5 intentos.")


@pytest.fixture(scope="module")
def company_id(client, organization_id):
    companies = client.get(
        f"{OPERATIONAL_CONTEXT}/api/v1/companies", params={"organization_identity_id": organization_id}
    ).json()["items"]
    if companies:
        return companies[0]["id"]
    response = client.post(f"{OPERATIONAL_CONTEXT}/api/v1/companies", json={"organization_identity_id": organization_id})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_register_member_by_username_against_real_keycloak(client, company_id, person_id):
    response = client.post(f"{OPERATIONAL_CONTEXT}/api/v1/companies/{company_id}/application-users", json={
        "username": "compras.test",
        "person_identity_id": person_id,
        "display_name": f"Validación {RUN_ID} (dato ficticio)",
    })

    if response.status_code == 503 and response.json().get("dependency") == "keycloak":
        pytest.skip("Keycloak Admin no disponible: renderice e importe el realm con operational-context-service.")
    assert response.status_code == 201, response.text
    assert response.json()["keycloak_user_id"] != "compras.test"  # se guarda el `sub`, no el username


def test_unknown_username_is_422_against_real_keycloak(client, company_id):
    # Persona sin membresía: el duplicado por persona se evalúa antes que la cuenta (orden del alta).
    response = client.post(f"{OPERATIONAL_CONTEXT}/api/v1/companies/{company_id}/application-users", json={
        "username": f"no-existe-{RUN_ID.lower()}",
        "person_identity_id": str(uuid4()),
        "display_name": "No existe",
    })

    assert response.status_code == 422, response.text
    assert response.json()["code"] == "OPERATIONAL_CONTEXT.KEYCLOAK_USER_NOT_FOUND"


def test_technical_access_evaluates_real_roles(client, company_id):
    """`admin.test` tiene `platform:lookup` por `perm:all:all:all`; se evalúan los roles de compras.test."""
    members = client.get(
        f"{OPERATIONAL_CONTEXT}/api/v1/companies/{company_id}/application-users",
    ).json()["items"]
    if not members:
        pytest.skip("La prueba anterior debía registrar el usuario operativo.")
    sub = members[0]["keycloak_user_id"]

    allowed = client.get(f"{OPERATIONAL_CONTEXT}/api/v1/operational-access", params={
        "company_id": company_id, "keycloak_user_id": sub, "permission": "perm:purchase:purchases:create",
    })
    denied = client.get(f"{OPERATIONAL_CONTEXT}/api/v1/operational-access", params={
        "company_id": company_id, "keycloak_user_id": sub, "permission": "perm:sales:sales:create",
    })

    assert allowed.status_code == denied.status_code == 200
    assert allowed.json()["allowed"] is True
    assert denied.json()["reason"] == "PERMISSION_DENIED"
