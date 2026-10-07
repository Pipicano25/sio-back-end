"""Utilidades de integración real de purchase-service (entorno integrado; secretos por entorno o `.env`).

Los datos se crean con los servicios reales y son **ficticios de validación**: organizaciones
`PRUEBA SIO COMPRAS … <ejecución>`, productos `Producto ficticio de validación COMPRAS <ejecución>`.
No se eliminan (compras, movimientos y operaciones son inmutables).
"""

from __future__ import annotations

import os
import random
import re
import secrets
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
RUN_ID = secrets.token_hex(4).upper()


def _base(variable: str, default: str) -> str:
    return os.environ.get(variable, default).rstrip("/")


PURCHASE = _base("PURCHASE_INTEGRATION_BASE_URL", "http://localhost:8107/api/v1")
PURCHASE_ROOT = PURCHASE.removesuffix("/api/v1")
INVENTORY = _base("INVENTORY_INTEGRATION_BASE_URL", "http://localhost:8109/api/v1")
OPERATIONAL_CONTEXT = _base("OPERATIONAL_CONTEXT_INTEGRATION_BASE_URL", "http://localhost:8104/api/v1")
COMMERCIAL_RELATIONSHIP = _base("COMMERCIAL_RELATIONSHIP_INTEGRATION_BASE_URL", "http://localhost:8106/api/v1")
PRODUCT_CATALOG = _base("PRODUCT_CATALOG_INTEGRATION_BASE_URL", "http://localhost:8103/api/v1")
PARTY_IDENTITY = _base("PARTY_IDENTITY_INTEGRATION_BASE_URL", "http://localhost:8101/api/v1")
PAYMENT_REFERENCE = _base("PAYMENT_REFERENCE_INTEGRATION_BASE_URL", "http://localhost:8105")
GEOGRAPHY = _base("GEOGRAPHY_INTEGRATION_BASE_URL", "http://localhost:8102")
AUDIT = _base("AUDIT_INTEGRATION_BASE_URL", "http://localhost:8110/api/v1")
TOKEN_URL = _base("KEYCLOAK_TOKEN_URL", "http://localhost:8081/realms/sio/protocol/openid-connect/token")


def secret(variable: str) -> str | None:
    value = os.environ.get(variable, "").strip()
    env_file = REPO_ROOT / "infrastructure" / ".env"
    if not value and env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            name, separator, content = line.partition("=")
            if separator and name.strip() == variable:
                value = content.strip().strip('"').strip("'")
    return value or None


class RenewingToken(httpx.Auth):
    """Pide el token y lo renueva 60 s antes de vencer (las pruebas largas superan su vida de 5 min)."""

    def __init__(self, data: dict) -> None:
        self._data = data
        self._token: str | None = None
        self._expires = 0.0

    def auth_flow(self, request):
        if self._token is None or time.monotonic() > self._expires - 60:
            body = httpx.post(TOKEN_URL, data=self._data, timeout=15).raise_for_status().json()
            self._token = body["access_token"]
            self._expires = time.monotonic() + float(body.get("expires_in", 300))
        request.headers["Authorization"] = f"Bearer {self._token}"
        yield request


def user_client(username: str) -> httpx.Client:
    password = secret("KEYCLOAK_TEST_USER_PASSWORD")
    if not password:
        pytest.skip("Defina KEYCLOAK_TEST_USER_PASSWORD (o infrastructure/.env).")
    data = {"grant_type": "password", "client_id": "sio-web", "scope": "openid", "username": username, "password": password}
    return httpx.Client(auth=RenewingToken(data), timeout=60)


def service_client(client_id: str, secret_variable: str) -> httpx.Client:
    client_secret = secret(secret_variable)
    if not client_secret:
        pytest.skip(f"Defina {secret_variable} (o infrastructure/.env).")
    data = {"grant_type": "client_credentials", "client_id": client_id, "client_secret": client_secret}
    return httpx.Client(auth=RenewingToken(data), timeout=60)


def require_services() -> None:
    for url in (
        f"{PURCHASE_ROOT}/health/ready",
        f"{INVENTORY.removesuffix('/api/v1')}/health/ready",
        f"{OPERATIONAL_CONTEXT.removesuffix('/api/v1')}/health/ready",
        f"{COMMERCIAL_RELATIONSHIP.removesuffix('/api/v1')}/health/ready",
        f"{PRODUCT_CATALOG.removesuffix('/api/v1')}/health/ready",
        f"{PARTY_IDENTITY.removesuffix('/api/v1')}/health/ready",
        f"{PAYMENT_REFERENCE}/health/live",
        f"{GEOGRAPHY}/health/live",
    ):
        try:
            httpx.get(url, timeout=5).raise_for_status()
        except httpx.HTTPError:
            pytest.skip(f"Servicio no disponible para integración: {url}")


def docker(*args: str) -> str:
    return subprocess.run(["docker", *args], capture_output=True, text=True, check=True).stdout.strip()


def wait_until(predicate, timeout: float, message: str) -> None:
    started = time.monotonic()
    while time.monotonic() - started < timeout:
        try:
            if predicate():
                return
        except httpx.HTTPError:
            pass
        time.sleep(1)
    pytest.fail(message)


# ---------------------------------------------------------------------------------------
# Datos ficticios con los servicios reales
# ---------------------------------------------------------------------------------------


def _first_id(client, url, **params) -> str:
    items = client.get(url, params=params).raise_for_status().json()["items"]
    if not items:
        pytest.skip(f"Sin datos en {url} {params}")
    return items[0]["id"]


def _conforming_number(pattern: str) -> str:
    regex = re.compile(pattern)
    for _ in range(200):
        base_length = random.randint(8, 10)
        base = str(random.randint(1, 9)) + "".join(random.choice("0123456789") for _ in range(base_length - 1))
        for candidate in (f"{base}-{random.randint(0, 9)}", base):
            if regex.fullmatch(candidate):
                return candidate
    pytest.skip(f"No se pudo generar un número que cumpla el patrón {pattern!r}.")


def _create_party(client, colombia, kind, sigla, path, payload) -> tuple[str, str]:
    rules = client.get(
        f"{PARTY_IDENTITY}/identification-type-rules",
        params={"party_kind": kind, "country_id": colombia, "sigla": sigla, "is_active": "true"},
    ).raise_for_status().json()["items"]
    if not rules:
        pytest.skip(f"Party Identity no tiene la regla {sigla} activa para Colombia (ejecute su seed).")
    for _ in range(5):
        number = _conforming_number(rules[0]["number_pattern"])
        response = client.post(f"{PARTY_IDENTITY}/{path}", json={**payload, "identification_number": number})
        if response.status_code == 201:
            return response.json()["id"], response.json()["identification_number"]
        if response.status_code != 409:
            pytest.fail(f"Party Identity respondió {response.status_code}: {response.text}")
    pytest.fail("No se obtuvo un número de identificación libre tras 5 intentos.")


def _organization(client, colombia, label: str) -> tuple[str, str]:
    return _create_party(client, colombia, "ORGANIZATION", "NIT", "organization-identities", {
        "country_id": colombia,
        "identification_type": "NIT",
        "legal_name": f"PRUEBA SIO COMPRAS {label}{RUN_ID} (DATO FICTICIO DE VALIDACION)",
    })


def _person(client, colombia, label: str) -> str:
    return _create_party(client, colombia, "PERSON", "CC", "person-identities", {
        "identification_country_id": colombia,
        "identification_type": "CC",
        "first_name": f"PRUEBACOMPRAS{label}{RUN_ID}",
        "last_name": "DATO FICTICIO DE VALIDACION",
        "birth_date": "1990-01-01",
    })[0]


def _member(client, company: str, username: str, person: str) -> str:
    response = client.post(f"{OPERATIONAL_CONTEXT}/companies/{company}/application-users", json={
        "username": username,
        "person_identity_id": person,
        "display_name": f"Validación COMPRAS {username} {RUN_ID} (dato ficticio)",
    })
    if response.status_code == 503:
        pytest.skip("Operational Context no pudo resolver el usuario en Keycloak Admin.")
    assert response.status_code == 201, response.text
    return response.json()["id"]


@dataclass(frozen=True)
class Product:
    company_product: str
    global_product: str
    unit: str
    box_presentation: str | None = None


def _adopt(client, company: str, label: str, *, inventory_control: bool, with_box: bool) -> Product:
    unit = _first_id(client, f"{PRODUCT_CATALOG}/units-of-measure", status="ACTIVE")
    category = client.post(f"{PRODUCT_CATALOG}/categories", json={
        "code": f"VAL-PUR-{label}-{RUN_ID}", "name": f"Categoría ficticia de validación COMPRAS {label} {RUN_ID}",
    })
    assert category.status_code == 201, category.text
    product = client.post(f"{PRODUCT_CATALOG}/products", json={
        "product_type": "GOOD",
        "canonical_name": f"Producto ficticio de validación COMPRAS {label} {RUN_ID}",
        "base_unit_id": unit,
    })
    assert product.status_code == 201, product.text
    product_id = product.json()["id"]
    assert client.post(
        f"{PRODUCT_CATALOG}/products/{product_id}/categories", json={"global_category_id": category.json()["id"]}
    ).status_code == 201
    assert client.post(f"{PRODUCT_CATALOG}/products/{product_id}/presentations", json={
        "code": f"UND-{label}-{RUN_ID}", "name": "Unidad (dato ficticio)", "is_base": True,
    }).status_code == 201
    box_global = None
    if with_box:
        box = client.post(f"{PRODUCT_CATALOG}/products/{product_id}/presentations", json={
            "code": f"CJ12-{label}-{RUN_ID}", "name": "Caja x12 (dato ficticio)", "base_quantity": "12",
            "display_order": 2, "is_base": False,
        })
        assert box.status_code == 201, box.text
        box_global = box.json()["id"]
    adopted = client.post(f"{COMMERCIAL_RELATIONSHIP}/companies/{company}/company-products", json={
        "global_product_id": product_id,
        "internal_code": f"PUR-{label}-{RUN_ID}",
        "display_name": f"Producto ficticio COMPRAS {label} {RUN_ID}",
        "currency_code": "COP",
        "sale_price": "1000.00",
        "inventory_control_enabled": inventory_control,
    })
    assert adopted.status_code == 201, adopted.text
    company_product = adopted.json()["id"]
    box_presentation = None
    if box_global:
        presentation = client.post(f"{COMMERCIAL_RELATIONSHIP}/companies/{company}/company-product-presentations", json={
            "company_product_id": company_product, "global_product_presentation_id": box_global,
            "sku": f"SKU-PUR-{label}-{RUN_ID}", "is_default_purchase": True,
        })
        assert presentation.status_code == 201, presentation.text
        box_presentation = presentation.json()["id"]
    return Product(company_product, product_id, unit, box_presentation)


@dataclass(frozen=True)
class RealWorld:
    company: str
    branch: str
    branch_b: str
    buyer_user: str
    supplier: str
    organization: str
    identification: str
    condition: str
    product: Product
    product_2: Product
    no_control: Product
    supplier_product: str
    foreign_company: str


def build_world(admin: httpx.Client) -> RealWorld:
    """Empresa COP con sucursal, `compras.test` y `admin.test` asignados, proveedor, condición CREDIT 30 y productos."""
    colombia = _first_id(admin, f"{GEOGRAPHY}/global-countries", iso3_code="COL")
    organization, _ = _organization(admin, colombia, "EMPRESA ")
    company = admin.post(f"{OPERATIONAL_CONTEXT}/companies", json={"organization_identity_id": organization})
    assert company.status_code == 201, company.text
    company_id = company.json()["id"]
    assert company.json()["default_currency"] == "COP", company.json()

    admin_user = _member(admin, company_id, "admin.test", _person(admin, colombia, "A"))
    buyer = _member(admin, company_id, "compras.test", _person(admin, colombia, "C"))
    _member(admin, company_id, "reportes.test", _person(admin, colombia, "R"))

    branch = admin.post(f"{OPERATIONAL_CONTEXT}/companies/{company_id}/branches", json={
        "code": f"PUR{RUN_ID}", "name": f"Bodega ficticia de validación COMPRAS {RUN_ID}",
    })
    assert branch.status_code == 201, branch.text
    branch_b = admin.post(f"{OPERATIONAL_CONTEXT}/companies/{company_id}/branches", json={
        "code": f"PURB{RUN_ID}", "name": f"Bodega B ficticia de validación COMPRAS {RUN_ID}",
    })
    assert branch_b.status_code == 201, branch_b.text
    for member in (buyer, admin_user):
        assigned = admin.post(
            f"{OPERATIONAL_CONTEXT}/application-users/{member}/user-branches", json={"branch_id": branch.json()["id"]}
        )
        assert assigned.status_code == 201, assigned.text

    supplier_org, supplier_number = _organization(admin, colombia, "PROVEEDOR ")
    supplier = admin.post(f"{COMMERCIAL_RELATIONSHIP}/companies/{company_id}/company-suppliers", json={
        "organization_identity_id": supplier_org, "internal_code": f"PRV-{RUN_ID}",
        "display_name": f"Proveedor ficticio COMPRAS {RUN_ID}",
    })
    assert supplier.status_code == 201, supplier.text

    types = admin.get(f"{PAYMENT_REFERENCE}/global-payment-condition-types", params={"page_size": 100})
    assert types.status_code == 200, types.text
    credit = next(item["id"] for item in types.json()["items"] if item["code"] == "CREDIT" and item["status"] == "ACTIVE")
    condition = admin.post(f"{COMMERCIAL_RELATIONSHIP}/companies/{company_id}/supplier-payment-conditions", json={
        "company_supplier_id": supplier.json()["id"], "payment_condition_type_id": credit, "currency_code": "COP",
        "payment_terms_days": 30, "valid_from": "2026-01-01T00:00:00Z",
    })
    assert condition.status_code == 201, condition.text

    product = _adopt(admin, company_id, "A", inventory_control=True, with_box=True)
    product_2 = _adopt(admin, company_id, "B", inventory_control=True, with_box=False)
    no_control = _adopt(admin, company_id, "S", inventory_control=False, with_box=False)
    supplier_product = admin.post(f"{COMMERCIAL_RELATIONSHIP}/companies/{company_id}/supplier-products", json={
        "company_supplier_id": supplier.json()["id"], "company_product_id": product.company_product,
        "company_product_presentation_id": product.box_presentation, "purchase_unit_id": product.unit,
        "currency_code": "COP", "expected_supplier_lead_time_hours": "48.50",
    })
    assert supplier_product.status_code == 201, supplier_product.text

    foreign_org, _ = _organization(admin, colombia, "AJENA ")
    foreign = admin.post(f"{OPERATIONAL_CONTEXT}/companies", json={"organization_identity_id": foreign_org})
    assert foreign.status_code == 201, foreign.text

    return RealWorld(
        company=company_id,
        branch=branch.json()["id"],
        branch_b=branch_b.json()["id"],
        buyer_user=buyer,
        supplier=supplier.json()["id"],
        organization=supplier_org,
        identification=f"NIT {supplier_number}",
        condition=condition.json()["id"],
        product=product,
        product_2=product_2,
        no_control=no_control,
        supplier_product=supplier_product.json()["id"],
        foreign_company=foreign.json()["id"],
    )


def draft_body(world: RealWorld, *lines: dict, **extra) -> dict:
    from datetime import date

    body = {"branch_id": world.branch, "company_supplier_id": world.supplier, "operation_date": date.today().isoformat(), "lines": list(lines)}
    body.update(extra)
    return body


def new_key() -> str:
    return f"integracion-{RUN_ID}-{uuid4()}"
