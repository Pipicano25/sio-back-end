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
        "currency_code": "COP",
    })

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "ACTIVE"
    assert "sale_price" not in body and "reference_cost" not in body  # spec 019

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


# --------------------------------------------------------------------------
# Fase B (specs/010-commercial-relationship-commercial-product, T085)
#
# Además de lo anterior exige Payment Reference en `PAYMENT_REFERENCE_INTEGRATION_BASE_URL`
# (por defecto `http://localhost:8105`, sin `/api/v1`), con su `seed` (`CASH`, `CREDIT`), y que el
# cliente técnico `commercial-relationship-service` tenga en el realm importado
# `perm:payment-reference:global_payment_condition_types:read` (plantilla del realm de la 010).
# Caída de Payment Reference: `docker stop sio-payment-reference-service` y repetir el alta de una
# condición; la respuesta es `503` con `dependency = payment-reference` (no se automatiza para no
# detener servicios compartidos).
# --------------------------------------------------------------------------

PAYMENT_REFERENCE = os.environ.get("PAYMENT_REFERENCE_INTEGRATION_BASE_URL", "http://localhost:8105").rstrip("/")


@pytest.fixture(scope="module")
def adopted_product(client, company_id):
    """Producto global nuevo y elegible (con su presentación base), adoptado en la empresa."""
    unit = _first_id(client, f"{PRODUCT_CATALOG}/units-of-measure", status="ACTIVE")
    category = client.post(f"{PRODUCT_CATALOG}/categories", json={
        "code": f"VAL-CRB-{RUN_ID}", "name": f"Categoría ficticia de validación CR Fase B {RUN_ID}",
    })
    assert category.status_code == 201, category.text
    product = client.post(f"{PRODUCT_CATALOG}/products", json={
        "product_type": "GOOD", "canonical_name": f"Producto ficticio de validación CR Fase B {RUN_ID}",
        "base_unit_id": unit,
    })
    assert product.status_code == 201, product.text
    product_id = product.json()["id"]
    assert client.post(f"{PRODUCT_CATALOG}/products/{product_id}/categories",
                       json={"global_category_id": category.json()["id"]}).status_code == 201
    presentation = client.post(f"{PRODUCT_CATALOG}/products/{product_id}/presentations", json={
        "code": f"CJ-{RUN_ID}", "name": "Caja (dato ficticio)", "is_base": True,
    })
    assert presentation.status_code == 201, presentation.text

    adopted = client.post(f"{COMMERCIAL_RELATIONSHIP}/companies/{company_id}/company-products", json={
        "global_product_id": product_id, "internal_code": f"VALB-{RUN_ID}",
        "display_name": f"Producto ficticio Fase B {RUN_ID}", "currency_code": "COP",
    })
    assert adopted.status_code == 201, adopted.text
    return {"global_product_id": product_id, "base_unit_id": unit,
            "global_presentation_id": presentation.json()["id"], "company_product": adopted.json()}


@pytest.fixture(scope="module")
def adopted_presentation(client, company_id, adopted_product):
    response = client.post(f"{COMMERCIAL_RELATIONSHIP}/companies/{company_id}/company-product-presentations", json={
        "company_product_id": adopted_product["company_product"]["id"],
        "global_product_presentation_id": adopted_product["global_presentation_id"],
        "sku": f"SKU-{RUN_ID}", "is_default_purchase": True,
    })
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture(scope="module")
def phase_b_supplier(client, company_id, colombia):
    organization = _organization(client, colombia, "proveedor Fase B")
    response = client.post(f"{COMMERCIAL_RELATIONSHIP}/companies/{company_id}/company-suppliers", json={
        "organization_identity_id": organization, "internal_code": f"PRVB-{RUN_ID}",
        "display_name": f"Proveedor ficticio Fase B {RUN_ID}",
    })
    assert response.status_code == 201, response.text
    return response.json()


def test_presentation_adoption_registers_first_use(client, adopted_product, adopted_presentation):
    assert adopted_presentation["is_default_purchase"] is True
    presentations = client.get(f"{PRODUCT_CATALOG}/products/{adopted_product['global_product_id']}/presentations").json()
    presentation = next(item for item in presentations if item["id"] == adopted_product["global_presentation_id"])
    assert presentation["first_used_at"] is not None


def test_supplier_product_with_real_base_unit(client, company_id, adopted_product, adopted_presentation, phase_b_supplier):
    url = f"{COMMERCIAL_RELATIONSHIP}/companies/{company_id}/supplier-products"
    body = {"company_supplier_id": phase_b_supplier["id"], "company_product_id": adopted_product["company_product"]["id"],
            "company_product_presentation_id": adopted_presentation["id"], "currency_code": "COP"}

    wrong = client.post(url, json={**body, "purchase_unit_id": str(uuid4())})
    assert wrong.status_code == 422, wrong.text
    assert wrong.json()["code"] == "COMMERCIAL_RELATIONSHIP.PURCHASE_UNIT_NOT_BASE_UNIT"

    created = client.post(url, json={**body, "purchase_unit_id": adopted_product["base_unit_id"]})
    assert created.status_code == 201, created.text


def test_payment_conditions_with_real_payment_reference(client, company_id, phase_b_supplier):
    types = client.get(f"{PAYMENT_REFERENCE}/global-payment-condition-types", params={"page_size": 100})
    if types.status_code != 200:
        pytest.skip(f"Payment Reference no disponible para integración: {types.status_code}")
    by_code = {item["code"]: item["id"] for item in types.json()["items"] if item["status"] == "ACTIVE"}
    url = f"{COMMERCIAL_RELATIONSHIP}/companies/{company_id}/supplier-payment-conditions"
    common = {"company_supplier_id": phase_b_supplier["id"], "currency_code": "COP"}

    cash_with_terms = client.post(url, json={**common, "payment_condition_type_id": by_code["CASH"], "payment_terms_days": 15})
    assert cash_with_terms.status_code == 422, cash_with_terms.text
    assert cash_with_terms.json()["code"] == "COMMERCIAL_RELATIONSHIP.PAYMENT_TERMS_INCONSISTENT"

    credit = client.post(url, json={**common, "payment_condition_type_id": by_code["CREDIT"], "payment_terms_days": 30,
                                    "credit_limit": "5000000.00", "is_default": True})
    assert credit.status_code == 201, credit.text
    assert "code" not in credit.json()


def test_price_list_change_price_and_applicable_price(client, company_id, adopted_product, adopted_presentation):
    price_list = client.post(f"{COMMERCIAL_RELATIONSHIP}/companies/{company_id}/price-lists", json={
        "code": f"LB-{RUN_ID}", "name": f"Lista ficticia {RUN_ID}", "currency_code": "COP", "is_default": True,
    })
    assert price_list.status_code == 201, price_list.text
    price = client.post(f"{COMMERCIAL_RELATIONSHIP}/companies/{company_id}/price-list-items", json={
        "price_list_id": price_list.json()["id"], "company_product_id": adopted_product["company_product"]["id"],
        "company_product_presentation_id": adopted_presentation["id"],
        "unit_price": "1500", "valid_from": "2026-01-01T00:00:00Z",
    })
    assert price.status_code == 201, price.text

    changed = client.post(f"{COMMERCIAL_RELATIONSHIP}/price-list-items/{price.json()['id']}/change-price",
                          json={"unit_price": "1600", "effective_from": "2099-01-01T00:00:00Z", "version": 1})
    assert changed.status_code == 201, changed.text

    resolved = client.post(f"{COMMERCIAL_RELATIONSHIP}/companies/{company_id}/applicable-prices/resolve", json={
        "at": "2027-01-01T00:00:00Z", "lines": [{"company_product_id": adopted_product["company_product"]["id"],
                                                 "company_product_presentation_id": adopted_presentation["id"]}],
    })
    assert resolved.status_code == 200, resolved.text
    line = resolved.json()["items"][0]
    assert (line["resolution"], line["unit_price"]) == ("PRICE_LIST_ITEM", "1500.00")


def test_service_account_reads_phase_b_with_lookup(service_token, adopted_presentation):
    response = httpx.get(
        f"{COMMERCIAL_RELATIONSHIP}/company-product-presentations/{adopted_presentation['id']}",
        headers={"Authorization": f"Bearer {service_token}"}, timeout=15,
    )
    # El cliente técnico de Commercial Relationship no tiene lectura de sus propios recursos: `403` sin
    # revelar el permiso (D3). Un consumidor (Purchase, Sales) recibirá lectura y `platform:lookup` en su Spec.
    assert response.status_code == 403
    assert "perm:" not in response.text


# ---- Escenarios de quickstart.md de la 010 con servicios reales (T093) ----


def _password_token(username: str) -> str:
    return httpx.post(TOKEN_URL, data={
        "grant_type": "password", "client_id": "sio-web", "scope": "openid",
        "username": username, "password": _secret(PASSWORD_VARIABLE),
    }, timeout=15).raise_for_status().json()["access_token"]


def test_quickstart_presentations_default_swap_and_rejections(client, company_id, adopted_product, adopted_presentation):
    """Escenarios 2 y 3: cambio atómico de predeterminada y presentación de otro producto."""
    product = adopted_product["company_product"]
    global_product = adopted_product["global_product_id"]
    second = client.post(f"{PRODUCT_CATALOG}/products/{global_product}/presentations", json={
        "code": f"SB-{RUN_ID}", "name": "Sobre (dato ficticio)", "base_quantity": "10", "is_base": False,
    })
    assert second.status_code == 201, second.text

    adopted = client.post(f"{COMMERCIAL_RELATIONSHIP}/companies/{company_id}/company-product-presentations", json={
        "company_product_id": product["id"], "global_product_presentation_id": second.json()["id"],
        "is_default_purchase": True,
    })
    assert adopted.status_code == 201, adopted.text
    previous = client.get(f"{COMMERCIAL_RELATIONSHIP}/company-product-presentations/{adopted_presentation['id']}").json()
    assert previous["is_default_purchase"] is False and previous["version"] == adopted_presentation["version"] + 1

    duplicate = client.post(f"{COMMERCIAL_RELATIONSHIP}/companies/{company_id}/company-product-presentations", json={
        "company_product_id": product["id"], "global_product_presentation_id": second.json()["id"],
    })
    assert duplicate.json()["code"] == "COMMERCIAL_RELATIONSHIP.DUPLICATE_PRESENTATION_ADOPTION"


def test_quickstart_prices_in_effect_explicit_list_history_and_access(client, company_id, foreign_company_id, adopted_product,
                                                                     adopted_presentation):
    """Escenarios 12, 14, 15, 16 y 17 con servicios reales."""
    product = adopted_product["company_product"]
    price_list = client.post(f"{COMMERCIAL_RELATIONSHIP}/companies/{company_id}/price-lists", json={
        "code": f"QS-{RUN_ID}", "name": "Lista quickstart (dato ficticio)", "currency_code": "COP",
    }).json()
    price = client.post(f"{COMMERCIAL_RELATIONSHIP}/companies/{company_id}/price-list-items", json={
        "price_list_id": price_list["id"], "company_product_id": product["id"], "unit_price": "2000",
        "company_product_presentation_id": adopted_presentation["id"],
        "valid_from": "2026-01-01T00:00:00Z", "valid_to": "2026-02-01T00:00:00Z",
    }).json()

    in_effect = client.put(f"{COMMERCIAL_RELATIONSHIP}/price-list-items/{price['id']}", json={
        "unit_price": "2100", "valid_from": price["valid_from"], "valid_to": price["valid_to"], "version": 1,
    })
    assert in_effect.json()["code"] == "COMMERCIAL_RELATIONSHIP.PRICE_IN_EFFECT_NOT_MODIFIABLE"

    resolve = f"{COMMERCIAL_RELATIONSHIP}/companies/{company_id}/applicable-prices/resolve"
    line = {"company_product_id": product["id"], "company_product_presentation_id": adopted_presentation["id"],
            "price_list_id": price_list["id"]}
    history = client.post(resolve, json={"at": "2026-01-15T00:00:00Z", "lines": [line]}).json()["items"][0]
    assert (history["resolution"], history["unit_price"]) == ("PRICE_LIST_ITEM", "2000.00")
    no_price = client.post(resolve, json={"at": "2027-01-01T00:00:00Z", "lines": [line]}).json()["items"][0]
    assert no_price["resolution"] == "NO_PRICE_IN_LIST" and no_price["unit_price"] is None

    inventory = {"Authorization": f"Bearer {_password_token('inventario.test')}"}
    assert httpx.get(f"{COMMERCIAL_RELATIONSHIP}/price-lists/{price_list['id']}", headers=inventory, timeout=15).status_code == 403
    sales = {"Authorization": f"Bearer {_password_token('ventas.test')}"}
    write = httpx.post(f"{COMMERCIAL_RELATIONSHIP}/companies/{company_id}/price-lists", headers=sales,
                       json={"code": "X", "name": "X", "currency_code": "COP"}, timeout=15)
    assert write.status_code == 403 and "perm:" not in write.text
    assert client.get(f"{COMMERCIAL_RELATIONSHIP}/companies/{foreign_company_id}/price-lists").status_code == 404
