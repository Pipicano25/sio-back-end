"""Paridad de ``v1_person_identities`` y ``v1_organization_identities`` con la API (spec 025, T036).

- Cada columna de la vista coincide con el mismo campo de ``GET /person-identities/{id}`` y
  ``GET /organization-identities/{id}``, para identidades activas e inactivas; una inexistente no tiene fila
  (``404`` en la API).
- La búsqueda de identidades ``ACTIVE`` que hace Sales (``GET /person-identities`` y ``/organization-identities``
  con ``status=ACTIVE``, ``search``, ``page`` y ``page_size``) se reproduce con ``PERSON_SEARCH_SQL`` /
  ``ORGANIZATION_SEARCH_SQL`` y sus consultas de conteo: mismo conjunto, mismo orden y mismo ``total_records``,
  para varias búsquedas y páginas. Esas consultas son la referencia que copia el adaptador de Sales.
- El rol lector de cada consumidor de ``contract/grants.yaml`` lee solo sus vistas y no las tablas de ``public``.
"""

from __future__ import annotations

import secrets
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from tests.conftest import organization_payload, person_payload

PROJECT_ROOT = Path(__file__).resolve().parents[2]
GRANTS = PROJECT_ROOT / "contract" / "grants.yaml"

PERSON_COLUMNS = (
    "id",
    "identification_type",
    "identification_number",
    "first_name",
    "middle_name",
    "last_name",
    "second_last_name",
    "status",
)
ORGANIZATION_COLUMNS = ("id", "identification_type", "identification_number", "legal_name", "trade_name", "status")

# --------------------------------------------------------------------------------------------------------------
# Consultas de referencia de la búsqueda de Sales (copiar tal cual en el adaptador de contrato).
#
# Parámetros:
#   :search     texto de búsqueda ya recortado (``strip``); NULL si viene vacío o solo con espacios, igual que
#               ``PersonIdentityFilters`` / ``OrganizationIdentityFilters``. El patrón es ``'%' || :search || '%'``
#               sin escapar ``%`` ni ``_``, como ``ilike(f"%{search}%")`` del repositorio.
#   :page_size  tamaño de página (> 0).
#   :offset     ``(page - 1) * page_size``.
# El total (``total_records``) sale de la consulta de conteo con el mismo WHERE; ``total_pages`` es
# ``ceil(total_records / page_size)`` y 0 si no hay registros.
# --------------------------------------------------------------------------------------------------------------

PERSON_WHERE = """
 WHERE status = 'ACTIVE'
   AND (CAST(:search AS text) IS NULL
        OR identification_number ILIKE '%' || CAST(:search AS text) || '%'
        OR first_name ILIKE '%' || CAST(:search AS text) || '%'
        OR middle_name ILIKE '%' || CAST(:search AS text) || '%'
        OR last_name ILIKE '%' || CAST(:search AS text) || '%'
        OR second_last_name ILIKE '%' || CAST(:search AS text) || '%')
"""

PERSON_SEARCH_SQL = (
    "SELECT id, identification_type, identification_number, first_name, middle_name, last_name, "
    "second_last_name, status FROM contract.v1_person_identities"
    + PERSON_WHERE
    + " ORDER BY last_name, first_name, id LIMIT :page_size OFFSET :offset"
)
PERSON_COUNT_SQL = "SELECT count(*) FROM contract.v1_person_identities" + PERSON_WHERE

ORGANIZATION_WHERE = """
 WHERE status = 'ACTIVE'
   AND (CAST(:search AS text) IS NULL
        OR identification_number ILIKE '%' || CAST(:search AS text) || '%'
        OR legal_name ILIKE '%' || CAST(:search AS text) || '%'
        OR trade_name ILIKE '%' || CAST(:search AS text) || '%')
"""

ORGANIZATION_SEARCH_SQL = (
    "SELECT id, identification_type, identification_number, legal_name, trade_name, status "
    "FROM contract.v1_organization_identities"
    + ORGANIZATION_WHERE
    + " ORDER BY legal_name, id LIMIT :page_size OFFSET :offset"
)
ORGANIZATION_COUNT_SQL = "SELECT count(*) FROM contract.v1_organization_identities" + ORGANIZATION_WHERE

PERSONS = (
    # (número, nombre, segundo nombre, apellido, segundo apellido, activa)
    ("1000000001", "ANA", None, "PRUEBA", None, True),
    ("1000000002", "ana", "maria", "Prueba", "Gomez", True),
    ("1000000003", "BEATRIZ", "ANA", "ZULUAGA", None, True),
    ("1000000004", "CARLOS", None, "ALVAREZ", "ANAYA", True),
    ("1000000005", "DIANA", None, "ALVAREZ", None, True),
    ("1000000006", "ANA", None, "PRUEBA", None, True),  # empata con la primera en apellido y nombre: decide id
    ("1000000007", "ANA", None, "PRUEBA", None, False),  # inactiva: no sale en la búsqueda
    ("2000000123", "ÉDGAR", "JOSÉ", "Ñuñez", "Peña", True),
    ("2000000124", "EDGAR", None, "NUNEZ", None, True),
    ("3000000001", "FABIO", None, "CASTRO_X", None, True),
    ("3000000002", "GLORIA", None, "CASTRO", "MEJIA", False),
    ("3000000003", "HUGO", "123", "BOTERO", None, True),
)

ORGANIZATIONS = (
    # (número, razón social, nombre comercial, activa)
    ("900000001-2", "ORGANIZACION FICTICIA S.A.S.", None, True),
    ("900000002-1", "organizacion ficticia s.a.s.", "FICTICIA", True),
    ("900000003-7", "ALFA LTDA", "ORGANIZACION ALFA", True),
    ("900000004-4", "ALFA LTDA", None, True),  # empata en razón social: decide id
    ("900000005-1", "BETA S.A.", "BETA", False),  # inactiva
    ("900000006-9", "ÑANDÚ S.A.", "Ñandu_Comercial", True),
    ("800000123-1", "GAMMA SAS", "GAMMA 123", True),
    ("800000124-7", "DELTA SAS", None, True),
)

PERSON_SEARCHES = (None, "", "   ", "ana", "  ANA ", "prueba", "alvarez", "1000000", "123", "ñuñez", "_", "%",
                   "NO-EXISTE", "Peña")
ORGANIZATION_SEARCHES = (None, "", "ficticia", "ALFA", "900000", "123", "ñand", "_", "%", "beta", "NO-EXISTE")
PAGINATION = ((1, 2), (2, 2), (3, 2), (1, 3), (2, 3), (1, 100), (9, 2))


def _view_row(connection, view: str, identity_id: str) -> dict | None:
    row = connection.execute(text(f"SELECT * FROM contract.{view} WHERE id = :id"), {"id": identity_id}).mappings().first()
    if row is None:
        return None
    return {key: (str(value) if value is not None and not isinstance(value, str) else value) for key, value in row.items()}


def _deactivate(api, resource: str, body: dict) -> None:
    response = api.post(f"/api/v1/{resource}/{body['id']}/deactivate", json={"version": body["version"]})
    assert response.status_code == 200, response.text


@pytest.fixture
def persons(api) -> list[dict]:
    created = []
    for number, first, middle, last, second_last, active in PERSONS:
        payload = person_payload(
            identification_number=number,
            first_name=first,
            middle_name=middle,
            last_name=last,
            second_last_name=second_last,
        )
        response = api.post("/api/v1/person-identities", json=payload)
        assert response.status_code == 201, response.text
        body = response.json()
        if not active:
            _deactivate(api, "person-identities", body)
        created.append(body)
    return created


@pytest.fixture
def organizations(api) -> list[dict]:
    created = []
    for number, legal_name, trade_name, active in ORGANIZATIONS:
        payload = organization_payload(identification_number=number, legal_name=legal_name, trade_name=trade_name)
        response = api.post("/api/v1/organization-identities", json=payload)
        assert response.status_code == 201, response.text
        body = response.json()
        if not active:
            _deactivate(api, "organization-identities", body)
        created.append(body)
    return created


def _normalized_search(search: str | None) -> str | None:
    """El mismo recorte que hacen los filtros HTTP de Party Identity."""
    return search.strip() if search and search.strip() else None


def _view_page(connection, page_sql: str, count_sql: str, search: str | None, page: int, page_size: int):
    params = {"search": _normalized_search(search), "page_size": page_size, "offset": (page - 1) * page_size}
    rows = connection.execute(text(page_sql), params).mappings().all()
    total = connection.execute(text(count_sql), {"search": params["search"]}).scalar_one()
    return [str(row["id"]) for row in rows], total


def _api_page(api, path: str, search: str | None, page: int, page_size: int):
    params = {"status": "ACTIVE", "page": str(page), "page_size": str(page_size)}
    if search:  # igual que HTTPPartyDirectory.search de Sales
        params["search"] = search
    response = api.get(path, params=params)
    assert response.status_code == 200, response.text
    body = response.json()
    return [item["id"] for item in body["items"]], body["total_records"]


# ---------------------------------------------------------------------------------------------- GET por id


def test_person_view_matches_get(api, persons, test_engine):
    with test_engine.connect() as connection:
        for created in persons:
            body = api.get(f"/api/v1/person-identities/{created['id']}").json()
            view = _view_row(connection, "v1_person_identities", created["id"])
            assert tuple(view) == PERSON_COLUMNS
            for column in PERSON_COLUMNS:
                assert view[column] == body[column], column
        statuses = connection.execute(text("SELECT DISTINCT status FROM contract.v1_person_identities")).scalars().all()
        assert set(statuses) == {"ACTIVE", "INACTIVE"}

        missing = str(uuid4())
        assert api.get(f"/api/v1/person-identities/{missing}").status_code == 404
        assert _view_row(connection, "v1_person_identities", missing) is None


def test_organization_view_matches_get(api, organizations, test_engine):
    with test_engine.connect() as connection:
        for created in organizations:
            body = api.get(f"/api/v1/organization-identities/{created['id']}").json()
            view = _view_row(connection, "v1_organization_identities", created["id"])
            assert tuple(view) == ORGANIZATION_COLUMNS
            for column in ORGANIZATION_COLUMNS:
                assert view[column] == body[column], column
        statuses = connection.execute(text("SELECT DISTINCT status FROM contract.v1_organization_identities")).scalars().all()
        assert set(statuses) == {"ACTIVE", "INACTIVE"}

        missing = str(uuid4())
        assert api.get(f"/api/v1/organization-identities/{missing}").status_code == 404
        assert _view_row(connection, "v1_organization_identities", missing) is None


def test_views_do_not_publish_private_fields(test_engine):
    with test_engine.connect() as connection:
        columns = {
            view: connection.execute(
                text("SELECT column_name FROM information_schema.columns WHERE table_schema = 'contract' "
                     "AND table_name = :v ORDER BY ordinal_position"),
                {"v": view},
            ).scalars().all()
            for view in ("v1_person_identities", "v1_organization_identities")
        }
    assert tuple(columns["v1_person_identities"]) == PERSON_COLUMNS
    assert tuple(columns["v1_organization_identities"]) == ORGANIZATION_COLUMNS


# ---------------------------------------------------------------------------------------------- búsqueda de Sales


def test_person_search_matches_api(api, persons, test_engine):
    checked_non_empty = 0
    with test_engine.connect() as connection:
        for search in PERSON_SEARCHES:
            for page, page_size in PAGINATION:
                expected = _api_page(api, "/api/v1/person-identities", search, page, page_size)
                actual = _view_page(connection, PERSON_SEARCH_SQL, PERSON_COUNT_SQL, search, page, page_size)
                assert actual == expected, (search, page, page_size)
                checked_non_empty += bool(expected[0])
    assert checked_non_empty > 20  # la comparación no es trivial


def test_organization_search_matches_api(api, organizations, test_engine):
    checked_non_empty = 0
    with test_engine.connect() as connection:
        for search in ORGANIZATION_SEARCHES:
            for page, page_size in PAGINATION:
                expected = _api_page(api, "/api/v1/organization-identities", search, page, page_size)
                actual = _view_page(connection, ORGANIZATION_SEARCH_SQL, ORGANIZATION_COUNT_SQL, search, page, page_size)
                assert actual == expected, (search, page, page_size)
                checked_non_empty += bool(expected[0])
    assert checked_non_empty > 15


def test_search_excludes_inactive_and_breaks_ties_by_id(api, persons, organizations, test_engine):
    inactive = {row["id"] for row in persons if row["identification_number"] in {"1000000007", "3000000002"}}
    ties = sorted(row["id"] for row in persons if row["identification_number"] in {"1000000001", "1000000006"})
    with test_engine.connect() as connection:
        ids, total = _view_page(connection, PERSON_SEARCH_SQL, PERSON_COUNT_SQL, None, 1, 100)
        assert not inactive & set(ids)
        assert total == len(PERSONS) - 2
        assert [identity for identity in ids if identity in ties] == ties

        org_ids, org_total = _view_page(connection, ORGANIZATION_SEARCH_SQL, ORGANIZATION_COUNT_SQL, "beta", 1, 10)
        assert (org_ids, org_total) == ([], 0)


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
        undeclared = {"v1_person_identities", "v1_organization_identities"} - set(views)
        forbidden = [f"contract.{view}" for view in sorted(undeclared)]
        forbidden += ["public.person_identities", "public.organization_identities", "public.identification_type_rules"]
        for relation in forbidden:
            with engine.connect() as connection, pytest.raises(DBAPIError, match="permission denied"):
                connection.execute(text(f"SELECT 1 FROM {relation} LIMIT 1"))
        with engine.connect() as connection, pytest.raises(DBAPIError, match="read-only"):
            connection.execute(text("CREATE TEMP TABLE pi_reader_probe (id int)"))
    finally:
        engine.dispose()
