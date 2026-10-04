"""Integración real con Keycloak, Operational Context, Product Catalog y Party Identity (T081).

Se ejecuta solo con `pytest -m integration` y exige el entorno integrado en ejecución
(`infrastructure/scripts/rebuild-all.sh`):

- Commercial Relationship en `COMMERCIAL_RELATIONSHIP_INTEGRATION_BASE_URL` (por defecto
  `http://localhost:8106`), configurado contra los mismos proveedores;
- Operational Context, Product Catalog, Party Identity y Geography en sus puertos publicados;
- Keycloak en `KEYCLOAK_TOKEN_URL`, con la contraseña de los usuarios de prueba en
  `KEYCLOAK_TEST_USER_PASSWORD` y el secreto del cliente técnico en
  `COMMERCIAL_RELATIONSHIP_INTEGRATION_CLIENT_SECRET` o, en su defecto,
  `COMMERCIAL_RELATIONSHIP_CLIENT_SECRET` de `infrastructure/.env` (nunca en el código; la variable
  de entorno homónima la fija `conftest.py` con un valor de prueba).

**Repetible**: cada ejecución crea en Party Identity una organización y una persona nuevas, en
Operational Context una empresa con `admin.test` como miembro y en Product Catalog un producto
global completo, todos con datos **ficticios de validación** marcados con el identificador de
ejecución. No depende de `DELETE`: los datos quedan en el entorno y no provocan `409` después.

Caída de un proveedor (`503`): detenga su contenedor (p. ej. `docker stop sio-product-catalog-service`)
y repita una adopción; la respuesta es `503 COMMERCIAL_RELATIONSHIP.DEPENDENCY_UNAVAILABLE` con
`dependency = product-catalog`. Se documenta aquí y no se automatiza para no detener servicios
compartidos.
"""

from __future__ import annotations

import base64
import json
import os
import random
import re
import secrets
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

from commercial_relationship_service.application.company_scope import is_technical_identity

pytestmark = pytest.mark.integration

REPO_ROOT = Path(__file__).resolve().parents[4]
PASSWORD_VARIABLE = "KEYCLOAK_TEST_USER_PASSWORD"
SECRET_VARIABLE = "COMMERCIAL_RELATIONSHIP_CLIENT_SECRET"
SECRET_OVERRIDE = "COMMERCIAL_RELATIONSHIP_INTEGRATION_CLIENT_SECRET"
CLIENT_ID = "commercial-relationship-service"

COMMERCIAL_RELATIONSHIP = os.environ.get(
    "COMMERCIAL_RELATIONSHIP_INTEGRATION_BASE_URL", "http://localhost:8106"
).rstrip("/") + "/api/v1"
OPERATIONAL_CONTEXT = os.environ.get("OPERATIONAL_CONTEXT_INTEGRATION_BASE_URL", "http://localhost:8104/api/v1").rstrip("/")
PRODUCT_CATALOG = os.environ.get("PRODUCT_CATALOG_INTEGRATION_BASE_URL", "http://localhost:8103/api/v1").rstrip("/")
PARTY_IDENTITY = os.environ.get("PARTY_IDENTITY_INTEGRATION_BASE_URL", "http://localhost:8101/api/v1").rstrip("/")
GEOGRAPHY = os.environ.get("GEOGRAPHY_INTEGRATION_BASE_URL", "http://localhost:8102").rstrip("/")
TOKEN_URL = os.environ.get(
    "KEYCLOAK_TOKEN_URL",
    "http://localhost:8081/realms/sio/protocol/openid-connect/token",
)
RUN_ID = secrets.token_hex(4).upper()


def _secret(variable: str, environment: str | None = None) -> str | None:
    value = os.environ.get(environment or variable, "").strip()
    env_file = REPO_ROOT / "infrastructure" / ".env"
    if not value and env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            name, separator, content = line.partition("=")
            if separator and name.strip() == variable:
                value = content.strip().strip('"').strip("'")
    return value or None


def _claims(token: str) -> dict:
    """Carga útil del JWT sin verificar firma: solo se inspeccionan los claims emitidos."""
    payload = token.split(".")[1]
    return json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))


@pytest.fixture(scope="module")
def client():
    password = _secret(PASSWORD_VARIABLE)
    if not password:
        pytest.skip(f"Defina {PASSWORD_VARIABLE} (o infrastructure/.env) para las pruebas de integración.")

    with httpx.Client(timeout=15) as http:
        for url in (
            COMMERCIAL_RELATIONSHIP.removesuffix("/api/v1") + "/health/ready",
            OPERATIONAL_CONTEXT.removesuffix("/api/v1") + "/health/ready",
            PRODUCT_CATALOG.removesuffix("/api/v1") + "/health/ready",
            PARTY_IDENTITY.removesuffix("/api/v1") + "/health/ready",
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
def service_token():
    secret = _secret(SECRET_VARIABLE, SECRET_OVERRIDE)
    if not secret:
        pytest.skip(f"Defina {SECRET_OVERRIDE} (o {SECRET_VARIABLE} en infrastructure/.env).")
    try:
        return httpx.post(TOKEN_URL, data={
            "grant_type": "client_credentials", "client_id": CLIENT_ID, "client_secret": secret,
        }, timeout=15).raise_for_status().json()["access_token"]
    except (httpx.HTTPError, KeyError):
        pytest.skip("Keycloak no emitió el token client_credentials del cliente técnico.")


def _first_id(client, url, **params) -> str:
    response = client.get(url, params=params)
    response.raise_for_status()
    items = response.json()["items"]
    if not items:
        pytest.skip(f"Sin datos en {url} {params}")
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


@pytest.fixture(scope="module")
def colombia(client):
    return _first_id(client, f"{GEOGRAPHY}/global-countries", iso3_code="COL")


def _create_party(client, colombia, kind, sigla, path, payload) -> str:
    rules = client.get(
        f"{PARTY_IDENTITY}/identification-type-rules",
        params={"party_kind": kind, "country_id": colombia, "sigla": sigla, "is_active": "true"},
    ).raise_for_status().json()["items"]
    if not rules:
        pytest.skip(f"Party Identity no tiene la regla {sigla} activa para Colombia (ejecute su seed).")

    for _ in range(5):
        response = client.post(f"{PARTY_IDENTITY}/{path}", json={
            **payload, "identification_number": _conforming_number(rules[0]["number_pattern"]),
        })
        if response.status_code == 201:
            return response.json()["id"]
        if response.status_code != 409:
            pytest.fail(f"Party Identity respondió {response.status_code}: {response.text}")
    pytest.fail("No se obtuvo un número de identificación libre tras 5 intentos.")


@pytest.fixture(scope="module")
def organization_id(client, colombia):
    return _organization(client, colombia, "")


@pytest.fixture(scope="module")
def person_id(client, colombia):
    """Persona nueva y exclusiva de esta ejecución (dato ficticio de validación)."""
    return _create_party(client, colombia, "PERSON", "CC", "person-identities", {
        "identification_country_id": colombia,
        "identification_type": "CC",
        "first_name": f"PRUEBACR{RUN_ID}",
        "last_name": "DATO FICTICIO DE VALIDACION",
        "birth_date": "1990-01-01",
    })


@pytest.fixture(scope="module")
def company_id(client, organization_id, person_id):
    """Empresa de esta ejecución con `admin.test` como miembro activo en Operational Context."""
    response = client.post(f"{OPERATIONAL_CONTEXT}/companies", json={"organization_identity_id": organization_id})
    assert response.status_code == 201, response.text
    company = response.json()["id"]

    member = client.post(f"{OPERATIONAL_CONTEXT}/companies/{company}/application-users", json={
        "username": "admin.test",
        "person_identity_id": person_id,
        "display_name": f"Validación CR {RUN_ID} (dato ficticio)",
    })
    if member.status_code == 503:
        pytest.skip("Operational Context no pudo resolver admin.test en Keycloak Admin.")
    assert member.status_code == 201, member.text
    return company


def _organization(client, colombia, label: str) -> str:
    """Organización nueva y exclusiva de esta ejecución (dato ficticio de validación)."""
    return _create_party(client, colombia, "ORGANIZATION", "NIT", "organization-identities", {
        "country_id": colombia,
        "identification_type": "NIT",
        "legal_name": f"PRUEBA SIO CR {label}{RUN_ID} (DATO FICTICIO DE VALIDACION)",
    })


@pytest.fixture(scope="module")
def foreign_company_id(client, colombia):
    """Empresa de esta ejecución en la que `admin.test` NO es miembro."""
    organization = _organization(client, colombia, "AJENA ")
    response = client.post(f"{OPERATIONAL_CONTEXT}/companies", json={"organization_identity_id": organization})
    assert response.status_code == 201, response.text
    return response.json()["id"]


@pytest.fixture(scope="module")
def global_product_id(client):
    """Producto global completo (categoría principal y presentación activas) y nunca usado."""
    unit = _first_id(client, f"{PRODUCT_CATALOG}/units-of-measure", status="ACTIVE")

    category = client.post(f"{PRODUCT_CATALOG}/categories", json={
        "code": f"VAL-CR-{RUN_ID}", "name": f"Categoría ficticia de validación CR {RUN_ID}",
    })
    assert category.status_code == 201, category.text

    product = client.post(f"{PRODUCT_CATALOG}/products", json={
        "product_type": "GOOD",
        "canonical_name": f"Producto ficticio de validación CR {RUN_ID}",
        "base_unit_id": unit,
    })
    assert product.status_code == 201, product.text
    product_id = product.json()["id"]

    assigned = client.post(
        f"{PRODUCT_CATALOG}/products/{product_id}/categories",
        json={"global_category_id": category.json()["id"]},
    )
    assert assigned.status_code == 201, assigned.text

    presentation = client.post(f"{PRODUCT_CATALOG}/products/{product_id}/presentations", json={
        "code": f"UND-{RUN_ID}", "name": "Unidad (dato ficticio)", "is_base": True,
    })
    assert presentation.status_code == 201, presentation.text

    detail = client.get(f"{PRODUCT_CATALOG}/products/{product_id}").json()
    if not detail["eligible_for_adoption"]:
        pytest.skip(f"El producto de validación no quedó elegible: {detail['completeness']}")
    assert detail["first_used_at"] is None
    return product_id


def test_adoption_registers_first_use_in_product_catalog(client, company_id, global_product_id):
    response = client.post(f"{COMMERCIAL_RELATIONSHIP}/companies/{company_id}/company-products", json={
        "global_product_id": global_product_id,
        "internal_code": f"VAL-{RUN_ID}",
        "display_name": f"Producto ficticio adoptado {RUN_ID}",
        "sale_price": "1500.00",
        "currency_code": "COP",
        "reference_cost": "1000.5000",
    })

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "ACTIVE"
    assert body["sale_price"] == "1500.00"
    assert body["reference_cost"] == "1000.5000"

    product = client.get(f"{PRODUCT_CATALOG}/products/{global_product_id}").json()
    assert product["first_used_at"] is not None

    duplicate = client.post(f"{COMMERCIAL_RELATIONSHIP}/companies/{company_id}/company-products", json={
        "global_product_id": global_product_id,
        "internal_code": f"OTRO-{RUN_ID}",
        "display_name": "Segunda adopción (dato ficticio)",
        "currency_code": "COP",
    })
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "COMMERCIAL_RELATIONSHIP.DUPLICATE_ADOPTION"


def test_unknown_global_product_is_422(client, company_id):
    response = client.post(f"{COMMERCIAL_RELATIONSHIP}/companies/{company_id}/company-products", json={
        "global_product_id": str(uuid4()),
        "internal_code": f"INX-{RUN_ID}",
        "display_name": "Producto inexistente (dato ficticio)",
        "currency_code": "COP",
    })

    assert response.status_code == 422
    assert response.json()["code"] == "COMMERCIAL_RELATIONSHIP.GLOBAL_PRODUCT_NOT_FOUND"


def test_customer_and_supplier_with_real_party_identity(client, company_id, organization_id, person_id):
    customer = client.post(f"{COMMERCIAL_RELATIONSHIP}/companies/{company_id}/company-customers", json={
        "customer_kind": "PERSON",
        "person_identity_id": person_id,
        "internal_code": f"CLI-{RUN_ID}",
        "display_name": f"Cliente ficticio {RUN_ID}",
    })
    assert customer.status_code == 201, customer.text
    assert customer.json()["status"] == "ACTIVE"

    supplier = client.post(f"{COMMERCIAL_RELATIONSHIP}/companies/{company_id}/company-suppliers", json={
        "organization_identity_id": organization_id,
        "internal_code": f"PRV-{RUN_ID}",
        "display_name": f"Proveedor ficticio {RUN_ID}",
        "preferred_contact_person_id": person_id,
    })
    # La organización es la propia empresa: la regla de autorrelación la rechaza (FR-031).
    assert supplier.status_code == 422, supplier.text
    assert supplier.json()["code"] == "COMMERCIAL_RELATIONSHIP.SELF_RELATIONSHIP_NOT_ALLOWED"


def test_supplier_with_other_real_organization(client, company_id, colombia, person_id):
    organization = _organization(client, colombia, "PROVEEDOR ")

    supplier = client.post(f"{COMMERCIAL_RELATIONSHIP}/companies/{company_id}/company-suppliers", json={
        "organization_identity_id": organization,
        "internal_code": f"PRV-{RUN_ID}",
        "display_name": f"Proveedor ficticio {RUN_ID}",
        "preferred_contact_person_id": person_id,
    })
    # `preferred_contact_person_id` es un contacto de Party Identity, no una persona (FR-031).
    assert supplier.status_code == 422, supplier.text
    assert supplier.json()["code"] == "COMMERCIAL_RELATIONSHIP.CONTACT_PERSON_INVALID"

    contact = client.post(f"{PARTY_IDENTITY}/organization-identities/{organization}/contact-persons", json={
        "person_identity_id": person_id, "position": "Contacto ficticio de validación",
    })
    assert contact.status_code == 201, contact.text

    supplier = client.post(f"{COMMERCIAL_RELATIONSHIP}/companies/{company_id}/company-suppliers", json={
        "organization_identity_id": organization,
        "internal_code": f"PRV-{RUN_ID}",
        "display_name": f"Proveedor ficticio {RUN_ID}",
        "preferred_contact_person_id": contact.json()["id"],
    })
    assert supplier.status_code == 201, supplier.text
    assert supplier.json()["status"] == "ACTIVE"


def test_user_without_membership_gets_404(client, foreign_company_id):
    response = client.get(f"{COMMERCIAL_RELATIONSHIP}/companies/{foreign_company_id}/company-products")

    assert response.status_code == 404
    assert response.json()["code"] == "COMMERCIAL_RELATIONSHIP.NOT_FOUND"


def test_real_tokens_and_technical_identity_predicate(client, service_token, company_id):
    """R-11 con tokens reales (T033): solo la cuenta de servicio cumple la correlación exacta."""
    service_claims = _claims(service_token)
    assert service_claims["client_id"] == CLIENT_ID
    assert service_claims["preferred_username"] == f"service-account-{CLIENT_ID}"
    assert is_technical_identity(service_claims) is True
    assert is_technical_identity(_claims(client.headers["Authorization"].removeprefix("Bearer "))) is False

    # El cliente técnico de CR no tiene permisos de CR ni `platform:lookup`: no hay exención.
    response = httpx.get(
        f"{COMMERCIAL_RELATIONSHIP}/companies/{company_id}/company-products",
        headers={"Authorization": f"Bearer {service_token}"},
        timeout=15,
    )
    assert response.status_code == 403
    assert response.json()["code"] == "COMMERCIAL_RELATIONSHIP.FORBIDDEN"


def test_company_summary_with_real_dependencies(client, company_id, organization_id):
    """FR-046: la empresa de la ejecución aparece con su razón social real y conteos coherentes."""
    page, found, total_pages = 1, None, 1
    while page <= total_pages and found is None:
        body = client.get(f"{COMMERCIAL_RELATIONSHIP}/company-summaries", params={"page": page, "page_size": 100})
        assert body.status_code == 200, body.text
        total_pages = body.json()["total_pages"]
        found = next((item for item in body.json()["items"] if item["company_id"] == company_id), None)
        page += 1

    assert found is not None, "La empresa de la ejecución no aparece en el resumen de admin.test."
    organization = client.get(f"{PARTY_IDENTITY}/organization-identities/{organization_id}").json()
    assert found["legal_name"] == organization["legal_name"]
    assert found["company_status"] == "ACTIVE"

    for resource in ("company_products", "company_customers", "company_suppliers"):
        listed = client.get(
            f"{COMMERCIAL_RELATIONSHIP}/companies/{company_id}/{resource.replace('_', '-')}",
            params={"status": "ALL", "page_size": 1},
        ).json()["total_records"]
        assert found[resource]["total"] == listed, resource

    default = client.get(f"{COMMERCIAL_RELATIONSHIP}/company-summaries").json()
    assert default["page_size"] == 1 and len(default["items"]) <= 1
