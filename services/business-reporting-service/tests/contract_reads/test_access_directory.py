"""`ContractOperationalContext.has_company_access` frente a `HTTPOperationalContext` (spec 025, T031).

BRS no tiene base propia: la prueba crea `business_reporting_test__oc` en el servidor de la base de pruebas
de Operational Context, con sus migraciones reales y el rol `brs_contract_reader`. La URL de administrador sale de
`CONTRACT_TEST_ADMIN_URL` o, si falta, de `OPERATIONAL_CONTEXT_TEST_DATABASE_URL` del `.env` de Operational
Context, como su `conftest.py`. Sin ninguna, la prueba se omite.
"""

from __future__ import annotations

import asyncio

import httpx
import pytest
from sio_contract_read import ContractReadSettings, create_contract_engine
from sio_contract_read.testing import create_owner_schema, provision_reader
from sio_contract_read.testing_oc import lock_access_tables, seed_access_world
from sqlalchemy import create_engine

from business_reporting_service.application.exceptions import DependencyUnavailableError
from business_reporting_service.infrastructure.contract_operational_context import ContractOperationalContext
from business_reporting_service.infrastructure.http_client import AsyncDependencyClient
from business_reporting_service.infrastructure.operational_context import HTTPOperationalContext
from tests.contract_reads.conftest import OC_OWNER as OWNER
from tests.contract_reads.conftest import claims

READ = "perm:operational-context:application_users:read"


def http(handler) -> HTTPOperationalContext:
    client = AsyncDependencyClient(provider="operational-context", base_url="http://oc.test/api/v1", timeout_seconds=3,
                                   transport=httpx.MockTransport(handler))
    return HTTPOperationalContext(client, "Bearer x")


def contract(engine, subject, *roles) -> ContractOperationalContext:
    return ContractOperationalContext(engine=engine, claims=claims(subject, *roles))


@pytest.fixture(scope="module")
def owner_url(contract_admin_url):
    return create_owner_schema(contract_admin_url, "business_reporting_test__oc", OWNER, recreate=True)


@pytest.fixture(scope="module")
def reader(owner_url, reader_password):
    url = provision_reader(owner_url, OWNER / "contract" / "grants.yaml", "business-reporting", reader_password)
    settings = ContractReadSettings(prefix="OPERATIONAL_CONTEXT", source="contract", database_url=url, timeout_seconds=2)
    engine = create_contract_engine(settings, application_name="brs-test")
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
    for case in cases:
        double = http(lambda request, case=case: httpx.Response(200, json=case.oc_body()))
        expected = asyncio.run(double.has_company_access(case.company_id))
        observed = asyncio.run(contract(reader, case.subject, READ).has_company_access(case.company_id))
        assert observed == expected, case.name
    assert any(case.expected.allowed for case in cases)


def test_missing_route_permission_is_false_like_403(reader, cases):
    allowed = next(case for case in cases if case.expected.allowed)
    assert asyncio.run(contract(reader, allowed.subject, "perm:business-reporting:all:read")
                       .has_company_access(allowed.company_id)) is False
    assert asyncio.run(http(lambda request: httpx.Response(403)).has_company_access(allowed.company_id)) is False


def test_database_down_is_unavailable(cases):
    settings = ContractReadSettings(
        prefix="OPERATIONAL_CONTEXT", source="contract", timeout_seconds=1, connect_timeout_seconds=1,
        database_url="postgresql+psycopg://brs_contract_reader:x@127.0.0.1:1/business_reporting_test__oc",
    )
    engine = create_contract_engine(settings, application_name="brs-test")
    try:
        with pytest.raises(DependencyUnavailableError) as info:
            asyncio.run(contract(engine, cases[0].subject, READ).has_company_access(cases[0].company_id))
        assert info.value.provider == "operational-context"
    finally:
        engine.dispose()


def test_slow_query_hits_statement_timeout(owner_url, reader, cases):
    owner = create_engine(owner_url)
    try:
        with lock_access_tables(owner):
            with pytest.raises(DependencyUnavailableError) as info:
                asyncio.run(contract(reader, cases[0].subject, READ).has_company_access(cases[0].company_id))
        assert info.value.cause == "contract:tiempo_agotado"
    finally:
        owner.dispose()
