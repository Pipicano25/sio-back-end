"""`ContractCompanyAccessDirectory` frente a `HTTPCompanyAccessDirectory` con los mismos datos (spec 025, T027).

Prepara en el contenedor de pruebas de Inventory la base `inventory_test__oc` con las migraciones reales de Operational
Context, crea el rol `inv_contract_reader` con `contract/grants.yaml` de Operational Context y comprueba:

- para toda la matriz de causas, el adaptador de contrato devuelve el mismo `AccessResult` que el adaptador HTTP
  cuando Operational Context responde lo que respondería con esos datos;
- sin el permiso de la ruta en el token → `OperationalAccessDeniedError`, como el `403` de hoy;
- base caída o consulta que supera el tiempo máximo → `DependencyUnavailableError("operational-context")`.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest
from sio_auth import TokenClaims
from sio_auth.permissions import extract_permission_grants
from sio_contract_read import ContractReadSettings, create_contract_engine
from sio_contract_read.testing import create_owner_schema, provision_reader
from sio_contract_read.testing_oc import lock_access_tables, seed_access_world
from sqlalchemy import create_engine

from inventory_service.application.exceptions import DependencyUnavailableError, OperationalAccessDeniedError
from inventory_service.infrastructure.contract_operational_context import ContractCompanyAccessDirectory as ContractAccessDirectory
from inventory_service.infrastructure.operational_context_directory import HTTPCompanyAccessDirectory as HTTPAccessDirectory

SERVICES = Path(__file__).resolve().parents[3]
OWNER = SERVICES / "operational-context-service"
READ = "perm:operational-context:application_users:read"


def claims(subject: str, *roles: str) -> TokenClaims:
    return TokenClaims(
        subject=subject,
        issuer="test",
        audiences=("sio-api",),
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
        roles=frozenset(roles),
        permissions=extract_permission_grants(roles),
        preferred_username=None,
        email=None,
        raw={},
    )


@pytest.fixture(scope="module")
def owner_url(test_database_url):
    return create_owner_schema(test_database_url, "inventory_test__oc", OWNER, recreate=True)


@pytest.fixture(scope="module")
def reader(owner_url):
    url = provision_reader(owner_url, OWNER / "contract" / "grants.yaml", "inventory", secrets.token_urlsafe(24))
    settings = ContractReadSettings(prefix="OPERATIONAL_CONTEXT", source="contract", database_url=url, timeout_seconds=2)
    engine = create_contract_engine(settings, application_name="inventory-service-test")
    yield engine
    engine.dispose()


@pytest.fixture(scope="module")
def cases(owner_url):
    engine = create_engine(owner_url)
    try:
        return seed_access_world(engine)
    finally:
        engine.dispose()


def http_double(case) -> HTTPAccessDirectory:
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=case.oc_body()))
    return HTTPAccessDirectory(base_url="http://oc.test/api/v1", authorization="Bearer x", timeout_seconds=2,
                               transport=transport)


def check(directory, case):
    return directory.check_branch(case.branch_id) if case.branch_id else directory.check_company(case.company_id)


def test_matrix_matches_http_adapter(reader, cases):
    assert len(cases) == 13
    for case in cases:
        contract = ContractAccessDirectory(engine=reader, claims=claims(case.subject, READ))
        assert check(contract, case) == check(http_double(case), case), case.name


def test_wildcard_read_permission_is_enough(reader, cases):
    case = cases[0]
    contract = ContractAccessDirectory(engine=reader, claims=claims(case.subject, "perm:all:all:read"))
    assert check(contract, case).allowed is True


def test_missing_route_permission_is_denied_like_403(reader, cases):
    case = cases[0]
    contract = ContractAccessDirectory(engine=reader, claims=claims(case.subject, "perm:inventory:all:read"))
    with pytest.raises(OperationalAccessDeniedError):
        check(contract, case)
    forbidden = httpx.MockTransport(lambda request: httpx.Response(403, json={}))
    http = HTTPAccessDirectory(base_url="http://oc.test/api/v1", authorization="Bearer x", timeout_seconds=2,
                               transport=forbidden)
    with pytest.raises(OperationalAccessDeniedError):
        check(http, case)


def test_database_down_is_unavailable(cases):
    settings = ContractReadSettings(
        prefix="OPERATIONAL_CONTEXT", source="contract", timeout_seconds=1, connect_timeout_seconds=1,
        database_url="postgresql+psycopg://inv_contract_reader:x@127.0.0.1:1/inventory_test__oc",
    )
    engine = create_contract_engine(settings, application_name="inventory-service-test")
    try:
        with pytest.raises(DependencyUnavailableError) as info:
            ContractAccessDirectory(engine=engine, claims=claims(cases[0].subject, READ)).check_company(cases[0].company_id)
        assert info.value.provider == "operational-context"
    finally:
        engine.dispose()


def test_slow_query_hits_statement_timeout(owner_url, reader, cases):
    owner = create_engine(owner_url)
    try:
        with lock_access_tables(owner):
            with pytest.raises(DependencyUnavailableError) as info:
                ContractAccessDirectory(engine=reader, claims=claims(cases[0].subject, READ)).check_company(
                    cases[0].company_id
                )
        assert info.value.cause == "contract:tiempo_agotado"
    finally:
        owner.dispose()


def test_reader_cannot_read_tables(reader):
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    with pytest.raises(DBAPIError, match="permission denied"):
        with reader.connect() as connection:
            connection.execute(text("SELECT 1 FROM public.application_users LIMIT 1"))


def test_is_member_matches_http_adapter(reader, cases):
    """Lecturas: miembro activo o empresa inactiva → True; no miembro o membresía inactiva → False (R-08)."""
    company_cases = [case for case in cases if case.branch_id is None]
    assert {case.expected.reason for case in company_cases} >= {None, "USER_NOT_MEMBER", "USER_MEMBERSHIP_INACTIVE",
                                                                "COMPANY_INACTIVE"}
    for case in company_cases:
        contract = ContractAccessDirectory(engine=reader, claims=claims(case.subject, READ))
        assert contract.is_member(case.company_id) == http_double(case).is_member(case.company_id), case.name
