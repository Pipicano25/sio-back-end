"""Utilidades de integración real de sales-service (entorno integrado; secretos por entorno o `.env`).

Los datos se crean con los servicios reales y son **ficticios de validación**: organizaciones y
personas `PRUEBA SIO VENTAS … <ejecución>`, productos `Producto ficticio de validación VENTAS
<ejecución>`. Las existencias se ingresan con una **compra real** confirmada en Purchase (flujo
compra → saldo → venta, SC-008). No se eliminan (ventas, compras, movimientos y operaciones son
inmutables).
"""

from __future__ import annotations

import os
import random
import re
import secrets
import subprocess
import time
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
RUN_ID = secrets.token_hex(4).upper()


def _base(variable: str, default: str) -> str:
    return os.environ.get(variable, default).rstrip("/")


SALES = _base("SALES_INTEGRATION_BASE_URL", "http://localhost:8108/api/v1")
SALES_ROOT = SALES.removesuffix("/api/v1")
PURCHASE = _base("PURCHASE_INTEGRATION_BASE_URL", "http://localhost:8107/api/v1")
INVENTORY = _base("INVENTORY_INTEGRATION_BASE_URL", "http://localhost:8109/api/v1")
OPERATIONAL_CONTEXT = _base("OPERATIONAL_CONTEXT_INTEGRATION_BASE_URL", "http://localhost:8104/api/v1")
COMMERCIAL_RELATIONSHIP = _base("COMMERCIAL_RELATIONSHIP_INTEGRATION_BASE_URL", "http://localhost:8106/api/v1")
PRODUCT_CATALOG = _base("PRODUCT_CATALOG_INTEGRATION_BASE_URL", "http://localhost:8103/api/v1")
PARTY_IDENTITY = _base("PARTY_IDENTITY_INTEGRATION_BASE_URL", "http://localhost:8101/api/v1")
GEOGRAPHY = _base("GEOGRAPHY_INTEGRATION_BASE_URL", "http://localhost:8102")
AUDIT = _base("AUDIT_INTEGRATION_BASE_URL", "http://localhost:8110/api/v1")
PAYMENT_REFERENCE = _base("PAYMENT_REFERENCE_INTEGRATION_BASE_URL", "http://localhost:8105")  # sin /api/v1

UNIT_PRESENTATION: dict[str, str] = {}
"""Producto de empresa → su presentación de factor 1 (spec 019: toda línea de venta indica su presentación)."""
DEFAULT_PRICE_LIST: dict[str, str] = {}
"""Empresa → su lista de precios predeterminada (spec 019: el precio es por presentación, no del producto)."""
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
    check_isolation()
    password = secret("KEYCLOAK_TEST_USER_PASSWORD")
    if not password:
        pytest.skip("Defina KEYCLOAK_TEST_USER_PASSWORD (o infrastructure/.env).")
    data = {"grant_type": "password", "client_id": "sio-web", "scope": "openid", "username": username, "password": password}
    return httpx.Client(auth=RenewingToken(data), timeout=60)


def service_client(client_id: str, secret_variable: str) -> httpx.Client:
    check_isolation()
    client_secret = secret(secret_variable)
    if not client_secret:
        pytest.skip(f"Defina {secret_variable} (o infrastructure/.env).")
    data = {"grant_type": "client_credentials", "client_id": client_id, "client_secret": client_secret}
    return httpx.Client(auth=RenewingToken(data), timeout=60)



def isolation_guard():
    """Barrera compartida `validation/isolation_guard.py` (incidente E2E del 2026-10-16), cargada por ruta."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("sio_isolation_guard", REPO_ROOT / "validation" / "isolation_guard.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_isolation() -> None:
    """Todos los destinos deben ser contenedores de la pila aislada; si no, la ejecución falla antes de escribir."""
    isolation_guard().check_targets({"purchase": PURCHASE, "sales": SALES, "inventory": INVENTORY, "operational_context": OPERATIONAL_CONTEXT, "commercial_relationship": COMMERCIAL_RELATIONSHIP, "product_catalog": PRODUCT_CATALOG, "party_identity": PARTY_IDENTITY, "payment_reference": PAYMENT_REFERENCE, "geography": GEOGRAPHY, "audit": AUDIT, "keycloak": TOKEN_URL})


def require_services() -> None:
    # Antes de cualquier solicitud: todos los destinos deben ser contenedores de la pila aislada; si no, falla.
    check_isolation()
    for url in (
        f"{SALES_ROOT}/health/ready",
        f"{PURCHASE.removesuffix('/api/v1')}/health/ready",
        f"{INVENTORY.removesuffix('/api/v1')}/health/ready",
        f"{OPERATIONAL_CONTEXT.removesuffix('/api/v1')}/health/ready",
        f"{COMMERCIAL_RELATIONSHIP.removesuffix('/api/v1')}/health/ready",
        f"{PRODUCT_CATALOG.removesuffix('/api/v1')}/health/ready",
        f"{PARTY_IDENTITY.removesuffix('/api/v1')}/health/ready",
        f"{GEOGRAPHY}/health/live",
    ):
        try:
            httpx.get(url, timeout=5).raise_for_status()
        except httpx.HTTPError:
            pytest.skip(f"Servicio no disponible para integración: {url}")


def docker(*args: str) -> str:
    return subprocess.run(["docker", *args], capture_output=True, text=True, check=True).stdout.strip()


ISOLATION_LABEL = "sio.integration.isolated"
CONTAINER_PREFIX = os.environ.get("SIO_INTEGRATION_CONTAINER_PREFIX", "sio-")


def container(name: str) -> str:
    """Contenedor aislado equivalente a `name` (`sio-purchase-db` → `<prefijo>purchase-db`).

    Las pruebas que detienen o alteran contenedores solo actúan sobre los que llevan la etiqueta
    `sio.integration.isolated=true`; un contenedor persistente nunca se detiene: la prueba se omite.
    """
    resolved = CONTAINER_PREFIX + name.removeprefix("sio-")
    try:
        label = docker("inspect", "-f", f'{{{{index .Config.Labels "{ISOLATION_LABEL}"}}}}', resolved)
    except (OSError, subprocess.CalledProcessError):
        pytest.skip(f"Contenedor aislado no disponible: {resolved}")
    if label != "true":
        pytest.skip(f"{resolved} no lleva {ISOLATION_LABEL}=true: no se detienen contenedores persistentes.")
    return resolved


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
        "legal_name": f"PRUEBA SIO VENTAS {label}{RUN_ID} (DATO FICTICIO DE VALIDACION)",
    })


def _person(client, colombia, label: str) -> tuple[str, str]:
    return _create_party(client, colombia, "PERSON", "CC", "person-identities", {
        "identification_country_id": colombia,
        "identification_type": "CC",
        "first_name": f"PRUEBAVENTAS{label}{RUN_ID}",
        "last_name": "DATO FICTICIO DE VALIDACION",
        "birth_date": "1990-01-01",
    })


def _member(client, company: str, username: str, person: str) -> str:
    response = client.post(f"{OPERATIONAL_CONTEXT}/companies/{company}/application-users", json={
        "username": username,
        "person_identity_id": person,
        "display_name": f"Validación VENTAS {username} {RUN_ID} (dato ficticio)",
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
    unit_presentation: str | None = None


def _adopt(client, company: str, label: str, *, sale_price: str, inventory_control: bool, with_box: bool,
           purchase_tax: str | None = "19") -> Product:
    unit = _first_id(client, f"{PRODUCT_CATALOG}/units-of-measure", status="ACTIVE")
    category = client.post(f"{PRODUCT_CATALOG}/categories", json={
        "code": f"VAL-SAL-{label}-{RUN_ID}", "name": f"Categoría ficticia de validación VENTAS {label} {RUN_ID}",
    })
    assert category.status_code == 201, category.text
    product = client.post(f"{PRODUCT_CATALOG}/products", json={
        "product_type": "GOOD",
        "canonical_name": f"Producto ficticio de validación VENTAS {label} {RUN_ID}",
        "base_unit_id": unit,
    })
    assert product.status_code == 201, product.text
    product_id = product.json()["id"]
    assert client.post(
        f"{PRODUCT_CATALOG}/products/{product_id}/categories", json={"global_category_id": category.json()["id"]}
    ).status_code == 201
    unit_global = client.post(f"{PRODUCT_CATALOG}/products/{product_id}/presentations", json={
        "code": f"UND-{label}-{RUN_ID}", "name": "Unidad (dato ficticio)", "is_base": True,
    })
    assert unit_global.status_code == 201, unit_global.text
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
        "internal_code": f"SAL-{label}-{RUN_ID}",
        "display_name": f"Producto ficticio VENTAS {label} {RUN_ID}",
        "currency_code": "COP",
        "inventory_control_enabled": inventory_control,
    })
    assert adopted.status_code == 201, adopted.text
    company_product = adopted.json()["id"]
    # Spec 021: sin tasa de impuesto de compra configurada no se confirma la compra; 19 % es una tasa **ficticia**.
    if purchase_tax is not None:
        taxed = client.put(f"{COMMERCIAL_RELATIONSHIP}/company-products/{company_product}/purchase-tax", json={
            "version": adopted.json()["version"], "purchase_tax_percentage": purchase_tax,
        })
        assert taxed.status_code == 200, taxed.text
    unit_presentation = client.post(f"{COMMERCIAL_RELATIONSHIP}/companies/{company}/company-product-presentations", json={
        "company_product_id": company_product, "global_product_presentation_id": unit_global.json()["id"],
        "sku": f"SKU-UND-{label}-{RUN_ID}",
    })
    assert unit_presentation.status_code == 201, unit_presentation.text
    UNIT_PRESENTATION[company_product] = unit_presentation.json()["id"]
    # Spec 019: el antiguo `sale_price` es ahora el precio explícito de la unidad en la lista predeterminada.
    unit_item = client.post(f"{COMMERCIAL_RELATIONSHIP}/companies/{company}/price-list-items", json={
        "price_list_id": DEFAULT_PRICE_LIST[company], "company_product_id": company_product,
        "company_product_presentation_id": unit_presentation.json()["id"], "unit_price": sale_price,
        "valid_from": "2026-01-01T00:00:00Z",
    })
    assert unit_item.status_code == 201, unit_item.text
    box_presentation = None
    if box_global:
        presentation = client.post(f"{COMMERCIAL_RELATIONSHIP}/companies/{company}/company-product-presentations", json={
            "company_product_id": company_product, "global_product_presentation_id": box_global,
            "sku": f"SKU-SAL-{label}-{RUN_ID}", "is_default_sale": True,
        })
        assert presentation.status_code == 201, presentation.text
        box_presentation = presentation.json()["id"]
    cover(client, company, [unit_presentation.json()["id"], box_presentation])
    return Product(company_product, product_id, unit, box_presentation, unit_presentation.json()["id"])


# Spec 021 (FR-021-35): una compra solo se confirma si cada presentación tiene política de ganancia aplicable. Cada
# empresa de prueba tiene una lista ficticia "COB-…" con una política del 30 % que cubre las presentaciones adoptadas;
# sus precios automáticos no se usan en las ventas de estas pruebas (otra lista).
COVERAGE: dict[str, dict] = {}


def cover(client, company: str, presentations: list[str]) -> str:
    """Agrega las presentaciones a la política de cobertura de la empresa (la crea la primera vez); devuelve la lista."""
    pending = [value for value in presentations if value]
    entry = COVERAGE.get(company)
    if entry is None:
        price_list = client.post(f"{COMMERCIAL_RELATIONSHIP}/companies/{company}/price-lists", json={
            "code": f"COB-{RUN_ID}", "name": f"Lista ficticia de cobertura {RUN_ID}", "currency_code": "COP",
        })
        assert price_list.status_code == 201, price_list.text
        policy = client.post(
            f"{COMMERCIAL_RELATIONSHIP}/companies/{company}/price-lists/{price_list.json()['id']}/pricing-policies",
            json={"name": f"Cobertura ficticia {RUN_ID}", "markup_percentage": "30",
                  "company_product_presentation_ids": pending[:100]},
        )
        assert policy.status_code == 201, policy.text
        entry = COVERAGE[company] = {"list": price_list.json()["id"], "policy": policy.json()}
        pending = pending[100:]
    for start in range(0, len(pending), 100):
        added = client.post(f"{COMMERCIAL_RELATIONSHIP}/pricing-policies/{entry['policy']['id']}/presentations", json={
            "version": entry["policy"]["version"], "company_product_presentation_ids": pending[start:start + 100],
        })
        assert added.status_code == 200, added.text
        entry["policy"] = added.json()
    return entry["list"]


@dataclass(frozen=True)
class RealWorld:
    company: str
    branch: str
    branch_b: str
    seller_user: str
    customer: str
    customer_identification: str
    customer_org: str
    customer_org_identification: str
    product: Product
    product_2: Product
    no_control: Product
    price_list: str
    box_item: str
    supplier: str
    foreign_company: str
    payment_method: str


def build_world(admin: httpx.Client) -> RealWorld:
    """Empresa COP con sucursales, usuarios asignados, clientes, productos con precio y lista de precios."""
    colombia = _first_id(admin, f"{GEOGRAPHY}/global-countries", iso3_code="COL")
    organization, _ = _organization(admin, colombia, "EMPRESA ")
    company = admin.post(f"{OPERATIONAL_CONTEXT}/companies", json={"organization_identity_id": organization})
    assert company.status_code == 201, company.text
    company_id = company.json()["id"]
    assert company.json()["default_currency"] == "COP", company.json()

    admin_user = _member(admin, company_id, "admin.test", _person(admin, colombia, "A")[0])
    seller = _member(admin, company_id, "ventas.test", _person(admin, colombia, "V")[0])
    supervisor = _member(admin, company_id, "supervisor.test", _person(admin, colombia, "S")[0])
    _member(admin, company_id, "reportes.test", _person(admin, colombia, "R")[0])

    branch = admin.post(f"{OPERATIONAL_CONTEXT}/companies/{company_id}/branches", json={
        "code": f"SAL{RUN_ID}", "name": f"Almacén ficticio de validación VENTAS {RUN_ID}",
    })
    assert branch.status_code == 201, branch.text
    branch_b = admin.post(f"{OPERATIONAL_CONTEXT}/companies/{company_id}/branches", json={
        "code": f"SALB{RUN_ID}", "name": f"Almacén B ficticio de validación VENTAS {RUN_ID}",
    })
    assert branch_b.status_code == 201, branch_b.text
    for member in (seller, admin_user, supervisor):
        assigned = admin.post(
            f"{OPERATIONAL_CONTEXT}/application-users/{member}/user-branches", json={"branch_id": branch.json()["id"]}
        )
        assert assigned.status_code == 201, assigned.text

    person, person_number = _person(admin, colombia, "CLIENTE")
    customer = admin.post(f"{COMMERCIAL_RELATIONSHIP}/companies/{company_id}/company-customers", json={
        "customer_kind": "PERSON", "person_identity_id": person, "internal_code": f"CLI-P-{RUN_ID}",
        "display_name": f"Cliente persona ficticio VENTAS {RUN_ID}",
    })
    assert customer.status_code == 201, customer.text
    customer_org_identity, customer_org_number = _organization(admin, colombia, "CLIENTE ")
    customer_org = admin.post(f"{COMMERCIAL_RELATIONSHIP}/companies/{company_id}/company-customers", json={
        "customer_kind": "ORGANIZATION", "organization_identity_id": customer_org_identity,
        "internal_code": f"CLI-O-{RUN_ID}", "display_name": f"Cliente organización ficticio VENTAS {RUN_ID}",
    })
    assert customer_org.status_code == 201, customer_org.text

    default_list = admin.post(f"{COMMERCIAL_RELATIONSHIP}/companies/{company_id}/price-lists", json={
        "code": f"DEF-{RUN_ID}", "name": f"Lista predeterminada ficticia VENTAS {RUN_ID}", "currency_code": "COP",
        "valid_from": "2026-01-01T00:00:00Z", "is_default": True,
    })
    assert default_list.status_code == 201, default_list.text
    DEFAULT_PRICE_LIST[company_id] = default_list.json()["id"]
    methods = admin.get(f"{PAYMENT_REFERENCE}/global-payment-methods", params={"page_size": 100})
    assert methods.status_code == 200, methods.text
    payment_method = next(item["id"] for item in methods.json()["items"] if item["code"] == "CASH" and item["status"] == "ACTIVE")

    product = _adopt(admin, company_id, "A", sale_price="1500.00", inventory_control=True, with_box=True)
    product_2 = _adopt(admin, company_id, "B", sale_price="9000.00", inventory_control=True, with_box=False)
    no_control = _adopt(admin, company_id, "S", sale_price="50000.00", inventory_control=False, with_box=False)

    price_list = admin.post(f"{COMMERCIAL_RELATIONSHIP}/companies/{company_id}/price-lists", json={
        "code": f"MAY-{RUN_ID}", "name": f"Lista mayorista ficticia VENTAS {RUN_ID}", "currency_code": "COP",
        "valid_from": "2026-01-01T00:00:00Z",
    })
    assert price_list.status_code == 201, price_list.text
    box_item = admin.post(f"{COMMERCIAL_RELATIONSHIP}/companies/{company_id}/price-list-items", json={
        "price_list_id": price_list.json()["id"], "company_product_id": product.company_product,
        "company_product_presentation_id": product.box_presentation, "unit_price": "16000.00",
        "valid_from": "2026-01-01T00:00:00Z",
    })
    assert box_item.status_code == 201, box_item.text

    supplier_org, _ = _organization(admin, colombia, "PROVEEDOR ")
    supplier = admin.post(f"{COMMERCIAL_RELATIONSHIP}/companies/{company_id}/company-suppliers", json={
        "organization_identity_id": supplier_org, "internal_code": f"PRV-{RUN_ID}",
        "display_name": f"Proveedor ficticio VENTAS {RUN_ID}",
    })
    assert supplier.status_code == 201, supplier.text

    foreign_org, _ = _organization(admin, colombia, "AJENA ")
    foreign = admin.post(f"{OPERATIONAL_CONTEXT}/companies", json={"organization_identity_id": foreign_org})
    assert foreign.status_code == 201, foreign.text

    world = RealWorld(
        company=company_id,
        branch=branch.json()["id"],
        branch_b=branch_b.json()["id"],
        seller_user=seller,
        customer=customer.json()["id"],
        customer_identification=f"CC {person_number}",
        customer_org=customer_org.json()["id"],
        customer_org_identification=f"NIT {customer_org_number}",
        product=product,
        product_2=product_2,
        no_control=no_control,
        price_list=price_list.json()["id"],
        box_item=box_item.json()["id"],
        supplier=supplier.json()["id"],
        foreign_company=foreign.json()["id"],
        payment_method=payment_method,
    )
    stock_with_purchase(admin, world, [(product, "200", "1000"), (product_2, "200", "6000")])
    return world


def adopt_product(admin: httpx.Client, world: RealWorld, label: str, *, sale_price: str = "2500.00",
                  purchase_tax: str | None = "19") -> Product:
    """Producto nuevo de la empresa del mundo, con control de inventario (spec 021: serie de costos propia)."""
    return _adopt(admin, world.company, label, sale_price=sale_price, inventory_control=True, with_box=False,
                  purchase_tax=purchase_tax)


def stock_with_purchase(admin: httpx.Client, world: RealWorld, lines: list[tuple[Product, str, str]]) -> dict:
    """Ingresa existencias con una compra real de contado, confirmada y **recibida** en Purchase (spec 020)."""
    sequences = admin.get(f"{PURCHASE}/companies/{world.company}/purchase-sequences").raise_for_status().json()["items"]
    if not any(item["is_active"] for item in sequences):
        created = admin.post(f"{PURCHASE}/companies/{world.company}/purchase-sequences", json={
            "series_code": "PRINCIPAL", "prefix": "CP", "separator": "-", "initial_number": 1, "number_length": 6,
            "reset_policy": "NEVER",
        })
        assert created.status_code == 201, created.text
    draft = admin.post(f"{PURCHASE}/companies/{world.company}/purchases", json={
        "branch_id": world.branch,
        "company_supplier_id": world.supplier,
        "operation_date": date.today().isoformat(),
        "payment_method_id": world.payment_method,
        "lines": [
            {
                "company_product_id": product.company_product,
                "company_product_presentation_id": product.unit_presentation,
                "quantity": quantity,
                "unit_cost": unit_cost,
            }
            for product, quantity, unit_cost in lines
        ],
    })
    assert draft.status_code == 201, draft.text
    confirmed = admin.post(
        f"{PURCHASE}/companies/{world.company}/purchases/{draft.json()['id']}/confirmation",
        json={"version": draft.json()["version"]},
        headers={"Idempotency-Key": new_key()},
    )
    assert confirmed.status_code == 200, confirmed.text
    received = admin.post(  # spec 020: solo la recepción física ingresa la mercancía
        f"{PURCHASE}/companies/{world.company}/purchases/{draft.json()['id']}/receipt",
        json={"version": confirmed.json()["version"], "full_receipt_confirmed": True},
        headers={"Idempotency-Key": new_key()},
    )
    assert received.status_code == 200, received.text
    return received.json()


def balance(client: httpx.Client, world: RealWorld, product: Product) -> Decimal:
    response = client.get(
        f"{INVENTORY}/companies/{world.company}/branches/{world.branch}/balances/{product.company_product}"
    ).raise_for_status()
    return Decimal(response.json()["quantity"])


def draft_body(world: RealWorld, *lines: dict, **extra) -> dict:
    """Spec 019: una línea sin presentación usa la de factor 1; spec 020: medio de pago declarado."""
    lines = tuple(
        line if "company_product_presentation_id" in line
        else {**line, "company_product_presentation_id": UNIT_PRESENTATION[line["company_product_id"]]}
        for line in lines
    )
    body = {
        "branch_id": world.branch,
        "company_customer_id": world.customer,
        "payment_method_id": world.payment_method,
        "lines": list(lines),
    }
    body.update(extra)
    return body


def new_key() -> str:
    return f"integracion-{RUN_ID}-{uuid4()}"
