"""PostgreSQL no disponible → `503` controlado y recuperación sin reinicio (Principio X; T016)."""

from __future__ import annotations

import threading
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from sales_service.api.errors import DATABASE_UNAVAILABLE_DETAIL
from tests.conftest import base, line, new_key, sale_body

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


def assert_controlled_503(response) -> None:
    assert response.status_code == 503, response.text
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["code"] == "SALES.DEPENDENCY_UNAVAILABLE"
    assert body["dependency"] == "database"
    assert body["detail"] == DATABASE_UNAVAILABLE_DETAIL
    assert not any(marker in response.text for marker in INTERNAL_MARKERS)


def test_routes_return_503_and_recover(app, seller, world, make_sequence, make_draft, as_token) -> None:
    make_sequence()
    draft = make_draft()
    url = f"{base(world)}/sales"
    calls = [
        lambda: seller.post(url, json=sale_body(world, line(world.product))),
        lambda: seller.get(url),
        lambda: seller.get(f"{url}/{draft['id']}"),
        lambda: seller.post(
            f"{url}/{draft['id']}/confirmation", json={"version": draft["version"]}, headers={"Idempotency-Key": new_key()}
        ),
        lambda: seller.get(f"{base(world)}/sale-sequences"),
        lambda: seller.get(f"{url}/{draft['id']}/availability"),
    ]
    with database_down(app):
        for call in calls:
            assert_controlled_503(call())
        assert as_token(None).get("/health/live").status_code == 200
        assert as_token(None).get("/health/ready").status_code == 503

    assert as_token(None).get("/health/ready").status_code == 200
    assert seller.get(f"{url}/{draft['id']}").status_code == 200


def test_lock_timeout_is_503(app, seller, world, make_draft, test_engine) -> None:
    draft = make_draft()
    app.state.database.lock_timeout_ms = 200
    locked = threading.Event()
    release = threading.Event()

    def hold() -> None:
        with test_engine.begin() as connection:
            connection.execute(text("SELECT 1 FROM sales WHERE id = :id FOR UPDATE"), {"id": draft["id"]})
            locked.set()
            release.wait(10)

    thread = threading.Thread(target=hold)
    thread.start()
    try:
        locked.wait(5)
        response = seller.post(
            f"{base(world)}/sales/{draft['id']}/details",
            json={**line(world.product_2), "version": draft["version"]},
        )
        assert_controlled_503(response)
    finally:
        release.set()
        thread.join()
