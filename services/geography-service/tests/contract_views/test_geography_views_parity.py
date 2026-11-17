"""Paridad de ``v1_countries``, ``v1_administrative_divisions`` y ``v1_cities`` con la API (spec 025, T067).

- Cada columna de la vista coincide con el mismo campo de ``GET /global-countries/{id}``,
  ``GET /global-administrative-divisions/{id}`` y ``GET /global-cities/{id}``, para filas activas e inactivas y
  para una ciudad sin división; un id inexistente no tiene fila (``404`` en la API).
- Las vistas solo publican esas columnas, en ese orden.
- El rol lector de cada consumidor de ``contract/grants.yaml`` lee solo sus vistas, no las tablas de ``public`` y no
  puede escribir.

Usa la base de pruebas de Geography (``GEOGRAPHY_TEST_DATABASE_URL``) con la app real y un JWKS local.
"""

from __future__ import annotations

import secrets
import time
from collections.abc import Generator
from pathlib import Path
from typing import Any
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from sio_auth import AuthSettings, SIOAuth
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from geography_service import main

PROJECT_ROOT = Path(__file__).resolve().parents[2]
GRANTS = PROJECT_ROOT / "contract" / "grants.yaml"
TEST_ISSUER = "https://keycloak.test/realms/sio"
TEST_AUDIENCE = "sio-api"
PERMISSIONS = ("perm:geography:all:all",)

COLUMNS = {
    "v1_countries": ("id", "status"),
    "v1_administrative_divisions": ("id", "country_id", "status"),
    "v1_cities": ("id", "country_id", "administrative_division_id", "status"),
}
ROUTES = {
    "v1_countries": "/global-countries",
    "v1_administrative_divisions": "/global-administrative-divisions",
    "v1_cities": "/global-cities",
}
TABLES = ("global_countries", "global_administrative_divisions", "global_cities")


class LocalJWKSClient:
    def __init__(self, public_key: Any) -> None:
        self._public_key = public_key

    def get_signing_key(self, kid: str) -> Any:
        return self._public_key

    def close(self) -> None:
        return None


@pytest.fixture(scope="module")
def rsa_private_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def client(monkeypatch, test_database_url: str, clean_database: None, rsa_private_key) -> Generator[TestClient, None, None]:
    test_auth = SIOAuth(
        AuthSettings(issuer=TEST_ISSUER, audience=TEST_AUDIENCE),
        jwks_client=LocalJWKSClient(rsa_private_key.public_key()),
    )
    monkeypatch.setenv("DATABASE_URL", test_database_url)
    monkeypatch.setattr(main.SIOAuth, "from_env", lambda: test_auth)
    now = int(time.time())
    token = jwt.encode(
        {
            "sub": "user-geography-contract",
            "iss": TEST_ISSUER,
            "aud": TEST_AUDIENCE,
            "iat": now,
            "exp": now + 600,
            "resource_access": {TEST_AUDIENCE: {"roles": list(PERMISSIONS)}},
        },
        rsa_private_key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )
    with TestClient(main.create_app(), headers={"Authorization": f"Bearer {token}"}) as test_client:
        yield test_client


def _create(client: TestClient, path: str, payload: dict) -> dict:
    response = client.post(path, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
def world(client) -> dict[str, list[dict]]:
    """Países, divisiones y ciudades en ambos estados; una ciudad sin división."""
    active = _create(client, "/global-countries", {"iso2_code": "ZZ", "iso3_code": "ZZZ", "name": "País ficticio",
                                                    "status": "ACTIVE"})
    inactive = _create(client, "/global-countries", {"iso2_code": "ZY", "iso3_code": "ZZY",
                                                      "name": "País ficticio inactivo", "status": "INACTIVE"})
    divisions = [
        _create(client, "/global-administrative-divisions", {"country_id": active["id"], "code": "D1",
                                                              "name": "División ficticia", "division_type": "DEPARTMENT",
                                                              "status": "ACTIVE"}),
        _create(client, "/global-administrative-divisions", {"country_id": inactive["id"], "code": "D2",
                                                              "name": "División ficticia inactiva",
                                                              "division_type": "STATE", "status": "INACTIVE"}),
    ]
    cities = [
        _create(client, "/global-cities", {"country_id": active["id"], "administrative_division_id": divisions[0]["id"],
                                           "code": "C1", "name": "Ciudad ficticia", "status": "ACTIVE"}),
        _create(client, "/global-cities", {"country_id": inactive["id"], "administrative_division_id": divisions[1]["id"],
                                           "code": "C2", "name": "Ciudad ficticia inactiva", "status": "INACTIVE"}),
        _create(client, "/global-cities", {"country_id": active["id"], "name": "Ciudad sin división",
                                           "status": "ACTIVE"}),
    ]
    return {"v1_countries": [active, inactive], "v1_administrative_divisions": divisions, "v1_cities": cities}


def _view_row(connection, view: str, row_id: str) -> dict | None:
    row = connection.execute(text(f"SELECT * FROM contract.{view} WHERE id = :id"), {"id": row_id}).mappings().first()
    if row is None:
        return None
    return {key: (None if value is None else str(value)) for key, value in row.items()}


@pytest.mark.parametrize("view", tuple(COLUMNS))
def test_view_matches_get_by_id(client, world, test_engine, view):
    statuses = set()
    with test_engine.connect() as connection:
        for created in world[view]:
            response = client.get(f"{ROUTES[view]}/{created['id']}")
            assert response.status_code == 200, response.text
            body = response.json()
            row = _view_row(connection, view, created["id"])
            assert tuple(row) == COLUMNS[view]
            for column in COLUMNS[view]:
                assert row[column] == body[column], column
            statuses.add(row["status"])

        missing = str(uuid4())
        assert client.get(f"{ROUTES[view]}/{missing}").status_code == 404
        assert _view_row(connection, view, missing) is None
    assert statuses == {"ACTIVE", "INACTIVE"}


def test_city_without_division_has_null_division(client, world, test_engine):
    city = world["v1_cities"][2]
    assert client.get(f"/global-cities/{city['id']}").json()["administrative_division_id"] is None
    with test_engine.connect() as connection:
        assert _view_row(connection, "v1_cities", city["id"])["administrative_division_id"] is None


def test_views_publish_only_contract_columns(test_engine):
    with test_engine.connect() as connection:
        for view, expected in COLUMNS.items():
            columns = connection.execute(
                text("SELECT column_name FROM information_schema.columns WHERE table_schema = 'contract' "
                     "AND table_name = :v ORDER BY ordinal_position"),
                {"v": view},
            ).scalars().all()
            assert tuple(columns) == expected, view


# ---------------------------------------------------------------------------------------------- roles lectores


def _reader_consumers() -> list[tuple[str, tuple[str, ...]]]:
    from sio_contract_read.provisioning import load_grants

    return [(consumer.service, consumer.views) for consumer in load_grants(GRANTS).consumers]


@pytest.mark.parametrize(("consumer", "views"), _reader_consumers(), ids=lambda value: value if isinstance(value, str) else "")
def test_reader_reads_declared_views_and_not_public_tables(test_database_url, test_engine, consumer, views):
    from sio_contract_read.testing import provision_reader

    url = provision_reader(test_database_url, GRANTS, consumer, secrets.token_urlsafe(24))
    engine = create_engine(url)
    try:
        for view in views:
            with engine.connect() as connection:
                connection.execute(text(f"SELECT 1 FROM contract.{view} LIMIT 1"))
        forbidden = [f"contract.{view}" for view in sorted(set(COLUMNS) - set(views))]
        forbidden += [f"public.{table}" for table in TABLES]
        for relation in forbidden:
            with engine.connect() as connection, pytest.raises(DBAPIError, match="permission denied"):
                connection.execute(text(f"SELECT 1 FROM {relation} LIMIT 1"))
        with engine.connect() as connection, pytest.raises(DBAPIError, match="read-only"):
            connection.execute(text("CREATE TEMP TABLE geo_reader_probe (id int)"))
    finally:
        engine.dispose()
