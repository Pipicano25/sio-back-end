"""Integración real con Party Identity y Keycloak (FR-027, FR-027a, T154).

Cierra el ítem "Implementar pruebas de integración con Party Identity" del bloque 6 de
`docs/development-roadmap.md` (gate `PRODUCT-CATALOG-CORE READY`). Contrato consumido:
`specs/002-product-catalog-service/contracts/party-identity-dependency.md`.

Se ejecuta solo con `pytest -m integration` y exige los servicios en ejecución:

- Product Catalog en `PRODUCT_CATALOG_INTEGRATION_BASE_URL` (por defecto
  `http://localhost:8103`, entorno integrado), configurado contra el mismo Party Identity;
- Party Identity en `PARTY_IDENTITY_INTEGRATION_BASE_URL` (con `/api/v1`, por defecto
  `http://localhost:8101/api/v1`) y Geography en `GEOGRAPHY_INTEGRATION_BASE_URL` (por defecto
  `http://localhost:8102`), con la regla NIT y los datos de Colombia cargados;
- Keycloak en `KEYCLOAK_TOKEN_URL`, con la contraseña de los usuarios de prueba en
  `KEYCLOAK_TEST_USER_PASSWORD` o en `infrastructure/.env` (nunca en el código).

**Repetible**: cada ejecución crea en Party Identity dos organizaciones nuevas con datos
**ficticios de validación** (razón social con prefijo `PRUEBA SIO PC <id de ejecución>`) y un
producto ficticio en Product Catalog. No depende de `DELETE`: quedan como datos de validación y no
provocan `409` en ejecuciones posteriores.

Caída del proveedor (`503`): detenga su contenedor (`docker stop sio-party-identity-service`) y
repita un alta con fabricante; la respuesta es `503 PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` y no se
guarda nada. Se documenta aquí y no se automatiza para no detener servicios compartidos.
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

PRODUCT_CATALOG = os.environ.get("PRODUCT_CATALOG_INTEGRATION_BASE_URL", "http://localhost:8103").rstrip("/")
PARTY_IDENTITY = os.environ.get("PARTY_IDENTITY_INTEGRATION_BASE_URL", "http://localhost:8101/api/v1").rstrip("/")
GEOGRAPHY = os.environ.get("GEOGRAPHY_INTEGRATION_BASE_URL", "http://localhost:8102").rstrip("/")
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
        for url in (
            f"{PRODUCT_CATALOG}/health/ready",
            f"{PARTY_IDENTITY.removesuffix('/api/v1')}/health/ready",
            f"{GEOGRAPHY}/health/live",
        ):
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


@pytest.fixture(scope="module")
def colombia_id(client) -> str:
    response = client.get(f"{GEOGRAPHY}/global-countries", params={"iso3_code": "COL"})
    response.raise_for_status()
    items = response.json()["items"]
    if not items:
        pytest.skip("Geography no tiene Colombia cargada.")
    return items[0]["id"]


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


def _create_organization(client, colombia_id: str, label: str) -> str:
    """Organización nueva y exclusiva de esta ejecución (datos ficticios de validación)."""
    rules = client.get(
        f"{PARTY_IDENTITY}/identification-type-rules",
        params={"party_kind": "ORGANIZATION", "country_id": colombia_id, "sigla": "NIT", "is_active": "true"},
    ).raise_for_status().json()["items"]
    if not rules:
        pytest.skip("Party Identity no tiene la regla NIT activa para Colombia (ejecute su seed).")

    for _ in range(5):
        response = client.post(f"{PARTY_IDENTITY}/organization-identities", json={
            "country_id": colombia_id,
            "identification_type": "NIT",
            "identification_number": _conforming_number(rules[0]["number_pattern"]),
            "legal_name": f"PRUEBA SIO PC {RUN_ID} {label} (DATO FICTICIO DE VALIDACION)",
        })
        if response.status_code == 201:
            return response.json()["id"]
        if response.status_code != 409:
            pytest.fail(f"Party Identity respondió {response.status_code}: {response.text}")
    pytest.fail("No se obtuvo un número de identificación libre tras 5 intentos.")


@pytest.fixture(scope="module")
def manufacturer_id(client, colombia_id) -> str:
    return _create_organization(client, colombia_id, "FABRICANTE A")


@pytest.fixture(scope="module")
def other_manufacturer_id(client, colombia_id) -> str:
    return _create_organization(client, colombia_id, "FABRICANTE B")


@pytest.fixture(scope="module")
def base_unit_id(client) -> str:
    response = client.get(f"{PRODUCT_CATALOG}/api/v1/units-of-measure", params={"limit": 100})
    response.raise_for_status()
    units = [unit for unit in response.json()["items"] if unit["code"] == "UND" and unit["status"] == "ACTIVE"]
    if not units:
        pytest.skip("Product Catalog no tiene la unidad UND activa (ejecute su seed).")
    return units[0]["id"]


def _product_body(base_unit_id: str, manufacturer: str | None, label: str) -> dict:
    return {
        "product_type": "GOOD",
        "canonical_name": f"Producto ficticio de validación {RUN_ID} {label}",
        "manufacturer_organization_id": manufacturer,
        "base_unit_id": base_unit_id,
    }


@pytest.fixture(scope="module")
def product(client, base_unit_id, manufacturer_id) -> dict:
    response = client.post(
        f"{PRODUCT_CATALOG}/api/v1/products",
        json=_product_body(base_unit_id, manufacturer_id, "CON FABRICANTE"),
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_create_product_with_real_manufacturer(product, manufacturer_id):
    assert product["manufacturer_organization_id"] == manufacturer_id
    assert product["status"] == "ACTIVE"


def test_change_manufacturer_to_another_real_organization(client, product, base_unit_id, other_manufacturer_id):
    body = _product_body(base_unit_id, other_manufacturer_id, "CON FABRICANTE")
    del body["product_type"]  # inmutable en la modificación
    body["version"] = product["version"]

    response = client.put(f"{PRODUCT_CATALOG}/api/v1/products/{product['id']}", json=body)

    assert response.status_code == 200, response.text
    assert response.json()["manufacturer_organization_id"] == other_manufacturer_id


def test_unknown_manufacturer_on_create_is_422(client, base_unit_id):
    response = client.post(
        f"{PRODUCT_CATALOG}/api/v1/products",
        json=_product_body(base_unit_id, str(uuid4()), "FABRICANTE INEXISTENTE"),
    )

    assert response.status_code == 422, response.text
    assert response.json()["code"] == "PRODUCT_CATALOG.MANUFACTURER_NOT_FOUND"


def test_unknown_manufacturer_on_update_is_422_and_keeps_product(client, product):
    current = client.get(f"{PRODUCT_CATALOG}/api/v1/products/{product['id']}").raise_for_status().json()
    body = {
        "canonical_name": current["canonical_name"],
        "description": current["description"],
        "global_brand_id": current["global_brand_id"],
        "manufacturer_organization_id": str(uuid4()),
        "base_unit_id": current["base_unit_id"],
        "version": current["version"],
    }

    response = client.put(f"{PRODUCT_CATALOG}/api/v1/products/{product['id']}", json=body)

    assert response.status_code == 422, response.text
    assert response.json()["code"] == "PRODUCT_CATALOG.MANUFACTURER_NOT_FOUND"
    after = client.get(f"{PRODUCT_CATALOG}/api/v1/products/{product['id']}").raise_for_status().json()
    assert after["version"] == current["version"]
    assert after["manufacturer_organization_id"] == current["manufacturer_organization_id"]


def test_trace_id_is_returned_with_real_dependency(client, base_unit_id):
    trace_id = secrets.token_hex(16)

    response = client.post(
        f"{PRODUCT_CATALOG}/api/v1/products",
        json=_product_body(base_unit_id, str(uuid4()), "TRAZA"),
        headers={"traceparent": f"00-{trace_id}-{secrets.token_hex(8)}-01"},
    )

    assert response.status_code == 422
    assert response.headers.get("X-Trace-Id") == trace_id
