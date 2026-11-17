"""Unidad base y tipo de condición por vistas de contrato frente a sus adaptadores HTTP (spec 025, T070).

Crea en el contenedor de pruebas de Commercial Relationship las bases ``commercial_relationship_test__ref_{pc,pr}``
con las migraciones reales de Product Catalog y Payment Reference, el rol ``cr_contract_reader`` con su
``contract/grants.yaml`` (una sola contraseña por ejecución: los roles son del servidor), y comprueba:

- ``ContractProductCatalogDirectory.get_product_base_unit`` y ``ContractPaymentReferenceDirectory.get_condition_type``
  devuelven lo mismo que el adaptador HTTP cuando el propietario responde lo que respondería con esos datos (filas
  activas e inactivas; el GET no filtra por estado);
- "no encontrado" igual que el ``404`` de hoy (``None``);
- base detenida → la misma ``DependencyUnavailableError(<proveedor>)`` que hoy produce el ``503``, con causa
  ``contract:``;
- ``lookup_product``, ``lookup_presentation`` y ``register_first_use`` siguen por HTTP (FR-036): el adaptador de
  contrato los delega sin tocar la base;
- con ``*_READ_SOURCE=contract`` las fábricas de ``main`` entregan los adaptadores de contrato, y con ``http`` (por
  defecto) los HTTP de siempre.
"""

from __future__ import annotations

import json
import secrets
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from sio_contract_read import ContractReadSettings, create_contract_engine
from sio_contract_read.testing import create_owner_schema, provision_reader
from sqlalchemy import create_engine, text

from commercial_relationship_service.application.exceptions import DependencyUnavailableError
from commercial_relationship_service.infrastructure.contract_payment_reference import (
    ContractPaymentReferenceDirectory,
)
from commercial_relationship_service.infrastructure.contract_product_catalog import ContractProductCatalogDirectory
from commercial_relationship_service.infrastructure.payment_reference_directory import (
    HTTPPaymentReferenceDirectory,
)
from commercial_relationship_service.infrastructure.product_catalog_directory import HTTPProductCatalogDirectory
from commercial_relationship_service.main import (
    build_contract_engines,
    build_payment_directory_factory,
    build_product_directory_factory,
)

SERVICES = Path(__file__).resolve().parents[3]
OWNERS = {"pc": "product-catalog-service", "pr": "payment-reference-service"}
CONSUMER = "commercial-relationship"
WHO = "prueba-spec-025"


# --------------------------------------------------------------------------- infraestructura


@pytest.fixture(scope="module")
def owners(test_database_url):
    """URL de administrador, motor de administrador y motor de lectura de cada propietario."""
    result = {}
    password = secrets.token_urlsafe(24)
    for key, service in OWNERS.items():
        owner = SERVICES / service
        url = create_owner_schema(test_database_url, f"commercial_relationship_test__ref_{key}", owner, recreate=True)
        reader_url = provision_reader(url, owner / "contract" / "grants.yaml", CONSUMER, password)
        settings = ContractReadSettings(prefix=key.upper(), source="contract", database_url=reader_url, timeout_seconds=2)
        result[key] = {
            "admin": create_engine(url),
            "settings": settings,
            "reader": create_contract_engine(settings, application_name="cr-t070"),
        }
    yield result
    for item in result.values():
        item["admin"].dispose()
        item["reader"].dispose()


def down_engine(key: str):
    settings = ContractReadSettings(
        prefix=key.upper(), source="contract", timeout_seconds=1, connect_timeout_seconds=1,
        database_url=f"postgresql+psycopg://cr_contract_reader:x@127.0.0.1:1/commercial_relationship_test__ref_{key}",
    )
    return create_contract_engine(settings, application_name="cr-t070")


class FakeTokens:
    def get_token(self) -> str:
        return "tecnico"

    def invalidate(self) -> None:
        pass


def routed(routes: dict, calls: list | None = None):
    """Doble HTTP: `(método, ruta)` → `(estado, cuerpo)`; lo demás `404`."""

    def handler(request: httpx.Request) -> httpx.Response:
        if calls is not None:
            calls.append((request.method, request.url.path))
        status, body = routes.get((request.method, request.url.path), (404, {}))
        return httpx.Response(status, json=body)

    return httpx.MockTransport(handler)


def http_catalog(routes: dict, calls: list | None = None) -> HTTPProductCatalogDirectory:
    return HTTPProductCatalogDirectory(base_url="http://pc.test/api/v1", timeout_seconds=2, token_client=FakeTokens(),
                                       transport=routed(routes, calls))


def http_payment(routes: dict) -> HTTPPaymentReferenceDirectory:
    return HTTPPaymentReferenceDirectory(base_url="http://pr.test", timeout_seconds=2, token_client=FakeTokens(),
                                         transport=routed(routes))


def insert(owners, key: str, table: str, **values) -> dict:
    columns = ", ".join(values)
    marks = ", ".join(f":{name}" for name in values)
    with owners[key]["admin"].begin() as connection:
        connection.execute(text(f"INSERT INTO public.{table} ({columns}) VALUES ({marks})"), values)
    return values


def audit() -> dict:
    now = datetime.now(UTC)
    return {"created_by": WHO, "updated_by": WHO, "created_at": now, "updated_at": now}


# --------------------------------------------------------------------------- datos


@pytest.fixture(scope="module")
def world(owners):
    tag = secrets.token_hex(3).upper()
    unit = insert(owners, "pc", "global_units_of_measure", id=uuid4(), code=f"U{tag}", name="Unidad ficticia",
                  symbol="u", measurement_type="UNIT", allows_decimals=False, **audit())
    products = {
        status: insert(owners, "pc", "global_products", id=uuid4(), product_type="GOOD", status=status,
                       canonical_name=f"PRODUCTO {status} {tag}", canonical_name_key=uuid4().hex,
                       base_unit_id=unit["id"], **audit())
        for status in ("ACTIVE", "INACTIVE")
    }
    types = {
        status: insert(owners, "pr", "global_payment_condition_types", id=uuid4(), code=f"T{status[:3]}{tag}",
                       name=f"Tipo {status}", description=None, status=status, **audit())
        for status in ("ACTIVE", "INACTIVE")
    }
    return {"unit": unit, "products": products, "types": types}


# --------------------------------------------------------------------------- Product Catalog


def test_product_base_unit_matches_http(owners, world):
    routes = {
        ("GET", f"/api/v1/products/{row['id']}"): (200, {"id": str(row["id"]), "status": row["status"],
                                                         "base_unit_id": str(row["base_unit_id"])})
        for row in world["products"].values()
    }
    calls: list = []
    double = http_catalog(routes)
    contract = ContractProductCatalogDirectory(engine=owners["pc"]["reader"], http=http_catalog({}, calls))
    for row in world["products"].values():
        expected = double.get_product_base_unit(row["id"])
        assert expected == world["unit"]["id"]
        assert contract.get_product_base_unit(row["id"]) == expected
    missing = uuid4()
    assert double.get_product_base_unit(missing) is None
    assert contract.get_product_base_unit(missing) is None
    assert calls == [], "la unidad base no debe consultar Product Catalog por HTTP"


def test_eligibility_and_first_use_stay_on_http(owners, world):
    """FR-036: `eligible_for_adoption` y `first-use` dependen de la lógica de Product Catalog."""
    product = world["products"]["ACTIVE"]["id"]
    presentation = uuid4()
    calls: list = []

    def lookup(request: httpx.Request):
        ids = json.loads(request.content)["ids"]
        return [{"id": value, "found": True, "status": "ACTIVE", "eligible_for_adoption": True,
                 "global_product_id": str(product)} for value in ids]

    routes = {
        ("POST", f"/api/v1/products/{product}/first-use"): (200, {}),
    }

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path))
        if request.url.path.endswith("/batch-lookup"):
            return httpx.Response(200, json={"items": lookup(request)})
        status, body = routes.get((request.method, request.url.path), (404, {}))
        return httpx.Response(status, json=body)

    http = HTTPProductCatalogDirectory(base_url="http://pc.test/api/v1", timeout_seconds=2, token_client=FakeTokens(),
                                       transport=httpx.MockTransport(handler))
    # Con la base caída: si alguno de estos métodos tocara la base, fallaría con 503.
    contract = ContractProductCatalogDirectory(engine=down_engine("pc"), http=http)
    assert contract.lookup_product(product) == http.lookup_product(product)
    assert contract.lookup_presentation(presentation) == http.lookup_presentation(presentation)
    contract.register_first_use(product)
    assert calls.count(("POST", "/api/v1/products/batch-lookup")) == 2
    assert calls.count(("POST", "/api/v1/presentations/batch-lookup")) == 2
    assert ("POST", f"/api/v1/products/{product}/first-use") in calls


# --------------------------------------------------------------------------- Payment Reference


def test_condition_type_matches_http(owners, world):
    routes = {
        ("GET", f"/global-payment-condition-types/{row['id']}"): (200, {"id": str(row["id"]), "code": row["code"],
                                                                         "name": row["name"], "status": row["status"]})
        for row in world["types"].values()
    }
    double = http_payment(routes)
    contract = ContractPaymentReferenceDirectory(engine=owners["pr"]["reader"])
    for row in world["types"].values():
        expected = double.get_condition_type(row["id"])
        assert expected is not None and expected.status == row["status"]
        assert contract.get_condition_type(row["id"]) == expected
    missing = uuid4()
    assert double.get_condition_type(missing) is None
    assert contract.get_condition_type(missing) is None


# --------------------------------------------------------------------------- base caída


def test_database_down_is_unavailable():
    pc, pr = down_engine("pc"), down_engine("pr")
    try:
        calls = [
            ("product-catalog", lambda: ContractProductCatalogDirectory(
                engine=pc, http=http_catalog({})).get_product_base_unit(uuid4())),
            ("payment-reference", lambda: ContractPaymentReferenceDirectory(engine=pr).get_condition_type(uuid4())),
        ]
        for provider, call in calls:
            with pytest.raises(DependencyUnavailableError) as info:
                call()
            assert info.value.provider == provider
            assert info.value.cause.startswith("contract:")
    finally:
        pc.dispose()
        pr.dispose()


# --------------------------------------------------------------------------- selección en main


def test_factories_select_source(owners, test_settings):
    import dataclasses

    http_engines = build_contract_engines(test_settings)
    assert http_engines.product_catalog is None and http_engines.payment_reference is None
    tokens = FakeTokens()
    assert isinstance(build_product_directory_factory(test_settings, tokens)(None), HTTPProductCatalogDirectory)
    assert isinstance(build_payment_directory_factory(test_settings, tokens)(None), HTTPPaymentReferenceDirectory)

    settings = dataclasses.replace(
        test_settings, product_catalog_reads=owners["pc"]["settings"], payment_reference_reads=owners["pr"]["settings"]
    )
    engines = build_contract_engines(settings)
    try:
        assert engines.product_catalog is not None and engines.payment_reference is not None
        product = build_product_directory_factory(settings, tokens, engines.product_catalog)(None)
        payment = build_payment_directory_factory(settings, tokens, engines.payment_reference)(None)
        assert isinstance(product, ContractProductCatalogDirectory)
        assert isinstance(payment, ContractPaymentReferenceDirectory)
    finally:
        engines.dispose()
