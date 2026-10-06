"""PostgreSQL no disponible → `503` controlado y recuperación sin reinicio (Principio X; T013).

La caída se simula apuntando el motor y la fábrica de sesiones de la misma instancia
`app.state.database` a un puerto cerrado; al restaurarlos, el mismo proceso vuelve a
responder sin reiniciarse. El `lock_timeout` agotado también es `503 database` (R-04).
"""

from __future__ import annotations

import threading
from contextlib import contextmanager
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from inventory_service.api.errors import DATABASE_UNAVAILABLE_DETAIL
from tests.conftest import line, operation_body, reversal_body

UNREACHABLE = "postgresql+psycopg://nadie:nada@127.0.0.1:1/ninguna"
INTERNAL_MARKERS = ("psycopg", "127.0.0.1", "SELECT", "Traceback", "nadie")


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


def _assert_controlled_503(response) -> None:
    assert response.status_code == 503, response.text
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["code"] == "INVENTORY.DEPENDENCY_UNAVAILABLE"
    assert body["dependency"] == "database"
    assert body["detail"] == DATABASE_UNAVAILABLE_DETAIL
    assert not any(marker in response.text for marker in INTERNAL_MARKERS)


def test_every_database_route_returns_503_and_recovers(app, operator, as_user, world, as_token) -> None:
    product = world.products[0]
    created = operator.post("/api/v1/inventory-entries", json=operation_body(world, line(product, "10")))
    assert created.status_code == 201, created.text
    operation_id = created.json()["id"]
    reader = as_user("inventario.test")
    base = f"/api/v1/companies/{world.company}"

    calls = [
        lambda: operator.post("/api/v1/inventory-entries", json=operation_body(world, line(product, "1"))),
        lambda: operator.post(
            "/api/v1/inventory-outputs", json=operation_body(world, line(product, "1"), origin_type="SALE")
        ),
        lambda: operator.post(f"/api/v1/inventory-entries/{operation_id}/reversal", json=reversal_body(world)),
        lambda: operator.post(f"/api/v1/inventory-outputs/{uuid4()}/reversal", json=reversal_body(world)),
        lambda: reader.get(f"{base}/branches/{world.branch}/balances"),
        lambda: reader.get(f"{base}/branches/{world.branch}/balances/{product}"),
        lambda: reader.post(f"{base}/branches/{world.branch}/balances/lookup", json={"company_product_ids": [str(product)]}),
        lambda: reader.get(f"{base}/branches/{world.branch}/kardex/{product}"),
        lambda: reader.get(f"{base}/inventory-operations/{operation_id}"),
        lambda: reader.get(f"{base}/inventory-operations/by-key/{uuid4()}"),
    ]

    with database_down(app):
        for call in calls:
            _assert_controlled_503(call())

        assert as_token(None).get("/health/live").status_code == 200
        ready = as_token(None).get("/health/ready")
        assert ready.status_code == 503
        assert ready.json() == {"status": "not_ready"}

    assert as_token(None).get("/health/ready").status_code == 200
    assert reader.get(f"{base}/branches/{world.branch}/balances/{product}").json()["quantity"] == "10.0000"
    assert operator.post("/api/v1/inventory-entries", json=operation_body(world, line(product, "1"))).status_code == 201


def test_lock_timeout_is_a_controlled_503(app, operator, world, test_engine) -> None:
    product = world.products[0]
    assert operator.post("/api/v1/inventory-entries", json=operation_body(world, line(product, "10"))).status_code == 201
    app.state.database.lock_timeout_ms = 300

    holding = threading.Event()
    release = threading.Event()

    def hold_lock() -> None:
        with test_engine.begin() as connection:
            connection.execute(text("SELECT 1 FROM inventory_balances FOR UPDATE"))
            holding.set()
            release.wait(10)

    holder = threading.Thread(target=hold_lock)
    holder.start()
    holding.wait(5)
    try:
        response = operator.post(
            "/api/v1/inventory-outputs", json=operation_body(world, line(product, "1"), origin_type="SALE")
        )
    finally:
        release.set()
        holder.join()

    _assert_controlled_503(response)
