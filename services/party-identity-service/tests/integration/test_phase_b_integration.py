"""Integración real de la Fase B con Keycloak, Geography y Operational Context (T099, FR-104).

Se ejecuta solo con `pytest -m integration` y exige los servicios en ejecución:

- Party Identity en `PARTY_IDENTITY_INTEGRATION_BASE_URL` (por defecto `http://localhost:8002`),
  configurado con `OPERATIONAL_CONTEXT_SERVICE_BASE_URL`, `GEOGRAPHY_SERVICE_BASE_URL` y las
  variables del cliente técnico `party-identity-service` (realm regenerado desde la plantilla, con
  `perm:operational-context:platform:lookup` y `perm:operational-context:application_users:read`);
- Operational Context en `OPERATIONAL_CONTEXT_INTEGRATION_BASE_URL` (por defecto
  `http://localhost:8004`), con al menos una empresa `ACTIVE` en la que el usuario de prueba elegido
  tenga membresía `ACTIVE` (ejercicio 4 de `services/operational-context-service/docs/ejemplo/`);
- Geography en `GEOGRAPHY_SERVICE_BASE_URL` con Colombia, Antioquia, Cundinamarca y Medellín;
- Keycloak en `KEYCLOAK_TOKEN_URL`; contraseña de los usuarios de prueba en
  `KEYCLOAK_TEST_USER_PASSWORD` o en `infrastructure/.env` (nunca en el código).

**Repetible:** cada ejecución crea una organización nueva con datos **ficticios de validación**
(razón social con prefijo `PRUEBA SIO PI <id>` y NIT único que cumple la regla vigente).

Caída de Operational Context (`503`, `dependency: operational-context`): detenga su contenedor y
registre una versión nueva de perfil. Se documenta aquí y no se automatiza para no detener
servicios compartidos.
"""

from __future__ import annotations

import os
import random
import re
import secrets
from pathlib import Path

import httpx
import pytest

pytestmark = pytest.mark.integration

REPO_ROOT = Path(__file__).resolve().parents[4]
PASSWORD_VARIABLE = "KEYCLOAK_TEST_USER_PASSWORD"

PARTY_IDENTITY = os.environ.get("PARTY_IDENTITY_INTEGRATION_BASE_URL", "http://localhost:8002").rstrip("/")
OPERATIONAL_CONTEXT = os.environ.get("OPERATIONAL_CONTEXT_INTEGRATION_BASE_URL", "http://localhost:8004").rstrip("/")
GEOGRAPHY = os.environ.get("GEOGRAPHY_SERVICE_BASE_URL", "http://localhost:8000").rstrip("/")
TOKEN_URL = os.environ.get("KEYCLOAK_TOKEN_URL", "http://localhost:8081/realms/sio/protocol/openid-connect/token")
CANDIDATE_USERS = ("supervisor.test", "admin.test")
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


def _token(http: httpx.Client, username: str, password: str) -> str:
    return http.post(TOKEN_URL, data={
        "grant_type": "password", "client_id": "sio-web", "scope": "openid",
        "username": username, "password": password,
    }).raise_for_status().json()["access_token"]


@pytest.fixture(scope="module")
def context():
    password = _password()
    if not password:
        pytest.skip(f"Defina {PASSWORD_VARIABLE} (o infrastructure/.env) para las pruebas de integración.")

    with httpx.Client(timeout=15) as http:
        for url in (f"{PARTY_IDENTITY}/health/ready", f"{OPERATIONAL_CONTEXT}/health/ready", f"{GEOGRAPHY}/health/live"):
            try:
                http.get(url).raise_for_status()
            except httpx.HTTPError:
                pytest.skip(f"Servicio no disponible para integración: {url}")

        for username in CANDIDATE_USERS:
            try:
                token = _token(http, username, password)
            except (httpx.HTTPError, KeyError):
                pytest.skip(f"No fue posible obtener el token de {username} en Keycloak.")
            headers = {"Authorization": f"Bearer {token}"}
            me = http.get(f"{OPERATIONAL_CONTEXT}/api/v1/me/operational-context", headers=headers)
            if me.status_code != 200:
                continue
            memberships = [
                item for item in me.json()["memberships"]
                if item["status"] == "ACTIVE" and item["company_status"] == "ACTIVE"
            ]
            if memberships:
                yield {
                    "http": http,
                    "headers": headers,
                    "username": username,
                    "company_id": memberships[0]["company_id"],
                    "application_user_id": memberships[0]["application_user_id"],
                    "member_companies": {item["company_id"] for item in me.json()["memberships"]},
                    "password": password,
                }
                return
        pytest.skip("Ningún usuario de prueba tiene una membresía ACTIVE en una empresa ACTIVE.")


def _first_id(context, url, **params) -> str:
    response = context["http"].get(url, params=params, headers=context["headers"])
    response.raise_for_status()
    items = response.json()["items"]
    if not items:
        pytest.skip(f"Sin datos en {url} {params}")
    return items[0]["id"]


@pytest.fixture(scope="module")
def geography(context):
    colombia = _first_id(context, f"{GEOGRAPHY}/global-countries", iso3_code="COL")
    antioquia = _first_id(context, f"{GEOGRAPHY}/global-administrative-divisions", country_id=colombia, search="Antioquia")
    cundinamarca = _first_id(context, f"{GEOGRAPHY}/global-administrative-divisions", country_id=colombia,
                             search="Cundinamarca")
    medellin = _first_id(context, f"{GEOGRAPHY}/global-cities", administrative_division_id=antioquia, search="Medell")
    return {"colombia": colombia, "antioquia": antioquia, "cundinamarca": cundinamarca, "medellin": medellin}


def _conforming_number(pattern: str) -> str:
    regex = re.compile(pattern)
    for _ in range(200):
        base = str(random.randint(1, 9)) + "".join(random.choice("0123456789") for _ in range(random.randint(7, 9)))
        for candidate in (f"{base}-{random.randint(0, 9)}", base):
            if regex.fullmatch(candidate):
                return candidate
    pytest.skip(f"No se pudo generar un número que cumpla el patrón {pattern!r}.")


@pytest.fixture(scope="module")
def organization_id(context, geography):
    rules = context["http"].get(
        f"{PARTY_IDENTITY}/api/v1/identification-type-rules",
        params={"party_kind": "ORGANIZATION", "country_id": geography["colombia"], "sigla": "NIT", "is_active": "true"},
        headers=context["headers"],
    )
    pattern = rules.json()["items"][0]["number_pattern"] if rules.status_code == 200 and rules.json()["items"] else r".+"
    response = context["http"].post(
        f"{PARTY_IDENTITY}/api/v1/organization-identities",
        json={
            "country_id": geography["colombia"],
            "identification_type": "NIT",
            "identification_number": _conforming_number(pattern),
            "legal_name": f"PRUEBA SIO PI {RUN_ID} S.A.S.",
        },
        headers=context["headers"],
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _profile(geography, company_id, **overrides) -> dict:
    payload = {
        "email": f"prueba-{RUN_ID.lower()}@ejemplo-ficticio.co",
        "phone": "+57 604 555 0199",
        "country_id": geography["colombia"],
        "administrative_division_id": geography["antioquia"],
        "city_id": geography["medellin"],
        "confirmed_by_company_id": company_id,
    }
    payload.update(overrides)
    return payload


def test_confirm_profile_with_real_geography_and_membership(context, geography, organization_id) -> None:
    response = context["http"].post(
        f"{PARTY_IDENTITY}/api/v1/organization-identities/{organization_id}/contact-profile",
        json=_profile(geography, context["company_id"]),
        headers=context["headers"],
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["confirmed_by_company_id"] == context["company_id"]
    assert body["confirmed_by_user_id"] == context["application_user_id"]


def test_incoherent_real_geography_is_rejected(context, geography, organization_id) -> None:
    current = context["http"].get(
        f"{PARTY_IDENTITY}/api/v1/organization-identities/{organization_id}/contact-profile", headers=context["headers"]
    ).json()

    response = context["http"].post(
        f"{PARTY_IDENTITY}/api/v1/organization-identities/{organization_id}/contact-profile",
        json=_profile(geography, context["company_id"], administrative_division_id=geography["cundinamarca"],
                      phone="+57 604 555 0198", version=current["version"]),
        headers=context["headers"],
    )

    assert response.status_code == 422, response.text
    assert response.json()["code"] == "PARTY_IDENTITY.GEOGRAPHY_INCOHERENT"


def test_company_without_membership_is_rejected(context, geography, organization_id) -> None:
    admin = context["http"].post(TOKEN_URL, data={
        "grant_type": "password", "client_id": "sio-web", "scope": "openid",
        "username": "admin.test", "password": context["password"],
    }).json()["access_token"]
    companies = context["http"].get(
        f"{OPERATIONAL_CONTEXT}/api/v1/companies", params={"page_size": 100},
        headers={"Authorization": f"Bearer {admin}"},
    ).json()["items"]
    foreign = next((item["id"] for item in companies if item["id"] not in context["member_companies"]), None)
    if foreign is None:
        pytest.skip("No hay una empresa ACTIVE sin membresía del usuario de prueba.")
    current = context["http"].get(
        f"{PARTY_IDENTITY}/api/v1/organization-identities/{organization_id}/contact-profile", headers=context["headers"]
    ).json()

    response = context["http"].post(
        f"{PARTY_IDENTITY}/api/v1/organization-identities/{organization_id}/contact-profile",
        json=_profile(geography, foreign, phone="+57 604 555 0197", version=current["version"]),
        headers=context["headers"],
    )

    assert response.status_code == 422, response.text
    assert response.json()["code"] == "PARTY_IDENTITY.CONFIRMATION_MEMBERSHIP_INVALID"
    assert response.json()["reason"] == "USER_NOT_MEMBER"


def test_reads_with_least_privilege_groups(context, organization_id) -> None:
    """Q-C1 con tokens reales: compras lee el perfil; consulta recibe 403."""
    statuses = {}
    for username in ("compras.test", "consulta.test"):
        try:
            token = _token(context["http"], username, context["password"])
        except (httpx.HTTPError, KeyError):
            pytest.skip(f"No fue posible obtener el token de {username}.")
        statuses[username] = context["http"].get(
            f"{PARTY_IDENTITY}/api/v1/organization-identities/{organization_id}/contact-profile",
            headers={"Authorization": f"Bearer {token}"},
        ).status_code

    assert statuses == {"compras.test": 200, "consulta.test": 403}
