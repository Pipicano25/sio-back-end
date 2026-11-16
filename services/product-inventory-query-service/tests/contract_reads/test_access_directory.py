"""`ContractOperationalContext.has_company_access` frente a `HTTPOperationalContext` (spec 025, T030).

PIQ no tiene base propia: la prueba crea `product_inventory_query_test__oc` en el servidor de la base de pruebas
de Operational Context, con sus migraciones reales y el rol `piq_contract_reader`. La URL de administrador sale de
`CONTRACT_TEST_ADMIN_URL` o, si falta, de `OPERATIONAL_CONTEXT_TEST_DATABASE_URL` del `.env` de Operational
Context, como su `conftest.py`. Sin ninguna, la prueba se omite.
"""

from __future__ import annotations

import asyncio
import os
import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest
from sio_auth.permissions import extract_permission_grants
from sio_auth.tokens import TokenClaims
from sio_contract_read import ContractReadSettings, create_contract_engine
from sio_contract_read.testing import create_owner_schema, provision_reader
from sio_contract_read.testing_oc import lock_access_tables, seed_access_world
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url

from product_inventory_query_service.application.exceptions import DependencyUnavailableError
from product_inventory_query_service.infrastructure.contract_operational_context import ContractOperationalContext
from product_inventory_query_service.infrastructure.http_client import AsyncDependencyClient
from product_inventory_query_service.infrastructure.operational_context import HTTPOperationalContext

SERVICES = Path(__file__).resolve().parents[3]
OWNER = SERVICES / "operational-context-service"
READ = "perm:operational-context:application_users:read"


def admin_url() -> str:
    url = os.environ.get("CONTRACT_TEST_ADMIN_URL", "").strip()
    if not url:
        # Sin `load_dotenv`: no debe dejar variables de Operational Context en el entorno de las demás pruebas.
        from dotenv import dotenv_values

        url = (dotenv_values(OWNER / ".env").get("OPERATIONAL_CONTEXT_TEST_DATABASE_URL") or "").strip()
    if not url:
        pytest.skip("Sin URL de una base de pruebas de Operational Context.")
    if "test" not in (make_url(url).database or ""):
        pytest.fail("La URL de administrador debe ser de una base de pruebas.")
    return url


def claims(subject: str, *roles: str) -> TokenClaims:
    return TokenClaims(
        subject=subject, issuer="test", audiences=("sio-api",), expires_at=datetime.now(UTC) + timedelta(minutes=5),
        roles=frozenset(roles), permissions=extract_permission_grants(roles), preferred_username=None, email=None,
        raw={},
    )


def http(handler) -> HTTPOperationalContext:
    client = AsyncDependencyClient(provider="operational-context", base_url="http://oc.test/api/v1", timeout_seconds=3,
                                   transport=httpx.MockTransport(handler))
    return HTTPOperationalContext(client, "Bearer x")


def contract(engine, subject, *roles, handler=None) -> ContractOperationalContext:
    return ContractOperationalContext(engine=engine, claims=claims(subject, *roles),
                                      http=http(handler or (lambda request: httpx.Response(500))))


@pytest.fixture(scope="module")
def owner_url():
    return create_owner_schema(admin_url(), "product_inventory_query_test__oc", OWNER, recreate=True)


@pytest.fixture(scope="module")
def reader(owner_url):
    url = provision_reader(owner_url, OWNER / "contract" / "grants.yaml", "product-inventory-query",
                           secrets.token_urlsafe(24))
    settings = ContractReadSettings(prefix="OPERATIONAL_CONTEXT", source="contract", database_url=url, timeout_seconds=2)
    engine = create_contract_engine(settings, application_name="piq-test")
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
    assert asyncio.run(contract(reader, allowed.subject, "perm:product-inventory-query:all:read")
                       .has_company_access(allowed.company_id)) is False
    assert asyncio.run(http(lambda request: httpx.Response(403)).has_company_access(allowed.company_id)) is False


def test_branches_still_use_http(reader, cases):
    calls = []

    def handler(request):
        calls.append(request.url.path)
        return httpx.Response(200, json={"items": [], "total": 0, "page": 1, "page_size": 100, "total_pages": 1})

    asyncio.run(contract(reader, cases[0].subject, READ, handler=handler).branches(cases[0].company_id,
                                                                                  status="ACTIVE"))
    assert calls and calls[0].endswith("/branches")


def test_database_down_is_unavailable(cases):
    settings = ContractReadSettings(
        prefix="OPERATIONAL_CONTEXT", source="contract", timeout_seconds=1, connect_timeout_seconds=1,
        database_url="postgresql+psycopg://piq_contract_reader:x@127.0.0.1:1/product_inventory_query_test__oc",
    )
    engine = create_contract_engine(settings, application_name="piq-test")
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
