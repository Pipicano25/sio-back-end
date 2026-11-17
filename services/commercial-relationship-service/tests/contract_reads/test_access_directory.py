"""`ContractCompanyAccessDirectory` frente a `HTTPCompanyAccessDirectory` con los mismos datos (spec 025, T028).

Prepara en el contenedor de pruebas de Commercial Relationship la base `commercial_relationship_test__oc` con las
migraciones reales de Operational Context y el rol `cr_contract_reader`, y comprueba:

- para las causas por empresa, `check_company_access` devuelve lo mismo que el adaptador HTTP con esos datos;
- sin el permiso de la ruta en el token → `OperationalAccessDeniedError`, como el `403` de hoy (FR-037);
- base caída o consulta lenta → `DependencyUnavailableError("operational-context")`;
- `list_member_companies` (desde la fase 6) la prueba `test_summary_reads.py`.
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

from commercial_relationship_service.application.exceptions import (
    DependencyUnavailableError,
    OperationalAccessDeniedError,
)
from commercial_relationship_service.infrastructure.contract_operational_context import ContractCompanyAccessDirectory
from commercial_relationship_service.infrastructure.operational_context_directory import HTTPCompanyAccessDirectory

SERVICES = Path(__file__).resolve().parents[3]
OWNER = SERVICES / "operational-context-service"
READ = "perm:operational-context:application_users:read"


def claims(subject: str, *roles: str) -> TokenClaims:
    return TokenClaims(
        subject=subject, issuer="test", audiences=("sio-api",), expires_at=datetime.now(UTC) + timedelta(minutes=5),
        roles=frozenset(roles), permissions=extract_permission_grants(roles), preferred_username=None, email=None,
        raw={},
    )


def http(handler) -> HTTPCompanyAccessDirectory:
    return HTTPCompanyAccessDirectory(base_url="http://oc.test/api/v1", authorization="Bearer x", timeout_seconds=2,
                                      transport=httpx.MockTransport(handler))


def contract(engine, subject, *roles):
    return ContractCompanyAccessDirectory(engine=engine, claims=claims(subject, *roles))


@pytest.fixture(scope="module")
def owner_url(test_database_url):
    return create_owner_schema(test_database_url, "commercial_relationship_test__oc", OWNER, recreate=True)


@pytest.fixture(scope="module")
def reader(owner_url):
    url = provision_reader(owner_url, OWNER / "contract" / "grants.yaml", "commercial-relationship",
                           secrets.token_urlsafe(24))
    settings = ContractReadSettings(prefix="OPERATIONAL_CONTEXT", source="contract", database_url=url, timeout_seconds=2)
    engine = create_contract_engine(settings, application_name="commercial-relationship-service-test")
    yield engine
    engine.dispose()


@pytest.fixture(scope="module")
def cases(owner_url):
    engine = create_engine(owner_url)
    try:
        return [case for case in seed_access_world(engine) if case.branch_id is None]
    finally:
        engine.dispose()


def test_company_causes_match_http_adapter(reader, cases):
    assert {case.expected.reason for case in cases} >= {None, "USER_NOT_MEMBER", "USER_MEMBERSHIP_INACTIVE",
                                                        "COMPANY_INACTIVE"}
    for case in cases:
        double = http(lambda request, case=case: httpx.Response(200, json=case.oc_body()))
        assert contract(reader, case.subject, READ).check_company_access(case.company_id) == \
            double.check_company_access(case.company_id), case.name


def test_missing_route_permission_is_denied_like_403(reader, cases):
    with pytest.raises(OperationalAccessDeniedError):
        contract(reader, cases[0].subject, "perm:commercial-relationship:all:read").check_company_access(
            cases[0].company_id
        )
    with pytest.raises(OperationalAccessDeniedError):
        http(lambda request: httpx.Response(403, json={})).check_company_access(cases[0].company_id)


def test_database_down_is_unavailable(cases):
    settings = ContractReadSettings(
        prefix="OPERATIONAL_CONTEXT", source="contract", timeout_seconds=1, connect_timeout_seconds=1,
        database_url="postgresql+psycopg://cr_contract_reader:x@127.0.0.1:1/commercial_relationship_test__oc",
    )
    engine = create_contract_engine(settings, application_name="cr-test")
    try:
        with pytest.raises(DependencyUnavailableError) as info:
            contract(engine, cases[0].subject, READ).check_company_access(cases[0].company_id)
        assert info.value.provider == "operational-context"
    finally:
        engine.dispose()


def test_slow_query_hits_statement_timeout(owner_url, reader, cases):
    owner = create_engine(owner_url)
    try:
        with lock_access_tables(owner):
            with pytest.raises(DependencyUnavailableError) as info:
                contract(reader, cases[0].subject, READ).check_company_access(cases[0].company_id)
        assert info.value.cause == "contract:tiempo_agotado"
    finally:
        owner.dispose()
