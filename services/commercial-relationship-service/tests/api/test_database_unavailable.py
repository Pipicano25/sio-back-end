"""PostgreSQL no disponible → `503` controlado y recuperación sin intervención (feature 009).

Se simula la caída apuntando el motor y la fábrica de sesiones de la **misma** instancia
`app.state.database` (la que usan las sesiones por solicitud y `/health/ready`) a un puerto cerrado; al
restaurarlos, el mismo proceso vuelve a responder sin reiniciarse.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from uuid import uuid4

import psycopg.errors as pg
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from commercial_relationship_service.api.errors import DATABASE_UNAVAILABLE_DETAIL
from tests.api.helpers import adopt, product_body

UNREACHABLE = "postgresql+psycopg://nadie:nada@127.0.0.1:1/ninguna"
INTERNAL_MARKERS = ("psycopg", "127.0.0.1", "SELECT", "Traceback", "nadie")


@pytest.fixture
def admin(as_user):
    return as_user("admin.test")


@pytest.fixture
def product(admin, company, fake_catalog) -> dict:
    """Producto empresarial adoptado con la base disponible."""
    return adopt(admin, company, fake_catalog)


@contextmanager
def database_down(app):
    database = app.state.database
    original_engine, original_sessions = database.engine, database.session_factory
    down = create_engine(UNREACHABLE, pool_pre_ping=True, connect_args={"connect_timeout": 2})
    database.engine = down
    database.session_factory = sessionmaker(bind=down, class_=Session, autoflush=False, expire_on_commit=False)
    try:
        yield
    finally:
        database.engine, database.session_factory = original_engine, original_sessions
        down.dispose()


@contextmanager
def failing_statements(app, orig: Exception):
    """Cada sentencia SQL falla con un `OperationalError` cuyo origen es `orig` (base disponible)."""

    def fail(*args, **kwargs):
        raise OperationalError("SELECT 1", {}, orig)

    engine = app.state.database.engine
    event.listen(engine, "before_cursor_execute", fail)
    try:
        yield
    finally:
        event.remove(engine, "before_cursor_execute", fail)


def _timed(request, *args, **kwargs):
    """Ejecuta una llamada y devuelve la respuesta con su duración (SC-002 es por respuesta)."""
    started = time.monotonic()
    response = request(*args, **kwargs)
    return response, time.monotonic() - started


def _assert_controlled_503(response) -> None:
    assert response.status_code == 503, response.text
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["code"] == "COMMERCIAL_RELATIONSHIP.DEPENDENCY_UNAVAILABLE"
    assert body["dependency"] == "database"
    assert body["detail"] == DATABASE_UNAVAILABLE_DETAIL
    assert body["status"] == 503 and body["trace_id"]
    assert not any(marker in response.text for marker in INTERNAL_MARKERS)


def test_endpoints_respond_controlled_503_while_database_is_down(app, admin, company, product, fake_catalog) -> None:
    new_product = product_body(fake_catalog.add(uuid4()), internal_code="000046")

    with database_down(app):
        results = [
            _timed(admin.get, f"/api/v1/companies/{company}/company-products"),
            _timed(admin.get, f"/api/v1/company-products/{product['id']}"),
            _timed(admin.post, f"/api/v1/companies/{company}/company-products", json=new_product),
            _timed(admin.post, f"/api/v1/company-products/{product['id']}/deactivate", json={"version": product["version"]}),
            _timed(admin.get, f"/api/v1/companies/{company}/company-customers"),
            _timed(admin.get, f"/api/v1/companies/{company}/company-suppliers"),
            _timed(admin.get, "/api/v1/company-summaries"),
        ]

    for response, elapsed in results:
        _assert_controlled_503(response)
        assert elapsed < 15  # tiempo acotado por respuesta (conexión con tiempo de espera)


def test_health_while_database_is_down(app, as_token) -> None:
    anonymous = as_token(None)
    with database_down(app):
        assert anonymous.get("/health/live").status_code == 200
        ready = anonymous.get("/health/ready")
        assert ready.status_code == 503
        assert ready.json() == {"status": "not_ready"}


def test_service_recovers_without_restart_and_leaves_no_partial_write(
    app, admin, as_token, company, product, fake_catalog
) -> None:
    listing = f"/api/v1/companies/{company}/company-products"
    new_product = product_body(fake_catalog.add(uuid4()), internal_code="000046")

    with database_down(app):
        _assert_controlled_503(admin.post(listing, json=new_product))

    assert as_token(None).get("/health/ready").status_code == 200
    assert admin.get(f"/api/v1/company-products/{product['id']}").status_code == 200
    assert admin.get(listing).json()["total_records"] == 1  # el alta interrumpida no quedó guardada
    assert admin.post(listing, json=new_product).status_code == 201
    assert admin.get(listing).json()["total_records"] == 2


@pytest.mark.parametrize(
    "orig",
    [pg.DeadlockDetected("deadlock detected"), pg.SerializationFailure("could not serialize access")],
    ids=["40P01", "40001"],
)
def test_other_postgresql_errors_keep_internal_error(app, admin, product, orig) -> None:
    with failing_statements(app, orig):
        response = admin.get(f"/api/v1/company-products/{product['id']}")

    assert response.status_code == 500
    assert response.json()["code"] == "COMMERCIAL_RELATIONSHIP.INTERNAL_ERROR"


def test_provider_unavailable_keeps_its_own_dependency(admin, company, fake_catalog) -> None:
    fake_catalog.lookup_unavailable = True
    response = admin.post(f"/api/v1/companies/{company}/company-products", json=product_body(uuid4()))

    assert response.status_code == 503
    assert response.json()["dependency"] == "product-catalog"


# --------------------------------------------------------------------------
# Fase B (T074; FR-100, Principio X): una lectura y una escritura por recurso nuevo
# --------------------------------------------------------------------------


def test_phase_b_routes_respond_controlled_503_and_recover(app, admin, company, product, fake_catalog, fake_party, fake_payment) -> None:
    from tests.api.helpers import (
        adopt_presentation,
        create_condition,
        create_price,
        create_price_list,
        create_supplier_product,
        supplier,
    )

    provider = supplier(admin, company, fake_party)
    presentation = adopt_presentation(admin, company, fake_catalog, product)
    supplier_product = create_supplier_product(admin, company, provider, product, fake_catalog)
    condition = create_condition(admin, company, provider, fake_payment)
    price_list = create_price_list(admin, company)
    price = create_price(admin, company, price_list, product)
    calls = [
        ("GET", f"/api/v1/company-product-presentations/{presentation['id']}", None),
        ("POST", f"/api/v1/company-product-presentations/{presentation['id']}/deactivate", {"version": 1}),
        ("GET", f"/api/v1/companies/{company}/supplier-products", None),
        ("POST", f"/api/v1/supplier-products/{supplier_product['id']}/deactivate", {"version": 1}),
        ("GET", f"/api/v1/supplier-payment-conditions/{condition['id']}", None),
        ("POST", f"/api/v1/supplier-payment-conditions/{condition['id']}/deactivate", {"version": 1}),
        ("GET", f"/api/v1/companies/{company}/price-lists", None),
        ("POST", f"/api/v1/price-lists/{price_list['id']}/deactivate", {"version": 1}),
        ("GET", f"/api/v1/price-list-items/{price['id']}", None),
        ("POST", f"/api/v1/price-list-items/{price['id']}/change-price", {"unit_price": "1", "version": 1}),
        ("POST", f"/api/v1/companies/{company}/applicable-prices/resolve", {"lines": [{"company_product_id": product["id"]}]}),
    ]

    with database_down(app):
        results = [_timed(admin.request, method, url, json=body) for method, url, body in calls]

    for response, elapsed in results:
        _assert_controlled_503(response)
        assert elapsed < 15

    # Recupera sin reinicio y sin escrituras parciales.
    assert admin.get(f"/api/v1/price-list-items/{price['id']}").json()["version"] == 1
    assert admin.get(f"/api/v1/company-product-presentations/{presentation['id']}").json()["status"] == "ACTIVE"
    resolved = admin.post(
        f"/api/v1/companies/{company}/applicable-prices/resolve",
        json={"lines": [{"company_product_id": product["id"], "price_list_id": price_list["id"]}]},
    )
    assert resolved.status_code == 200 and resolved.json()["items"][0]["resolution"] == "PRICE_LIST_ITEM"
