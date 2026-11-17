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
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from product_inventory_query_service.application.exceptions import DependencyUnavailableError
from product_inventory_query_service.application.ports import BranchInfo
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


BRANCHES = "perm:operational-context:branches:read"


def _expected_branches(owner_url, company_id, status):
    """Lo que hoy lista `GET /companies/{c}/branches?status=` (orden `created_at`, `id`)."""
    engine = create_engine(owner_url)
    try:
        with engine.connect() as connection:
            rows = connection.execute(text("SELECT id, company_id, status FROM branches WHERE company_id = :c AND status = :s"
                                           " ORDER BY created_at, id"), {"c": company_id, "s": status}).all()
    finally:
        engine.dispose()
    return [BranchInfo(row.id, row.company_id, row.status) for row in rows]


def _http_branches(branches):
    body = {"items": [{"id": str(b.id), "company_id": str(b.company_id), "status": b.status} for b in branches],
            "page": 1, "page_size": 100, "total_records": len(branches), "total_pages": 1}
    return http(lambda request: httpx.Response(200, json=body))


def test_branches_match_http_for_a_member(owner_url, reader, cases):
    """Historia 6: las sucursales se leen de `v1_branches`, con el mismo resultado y orden que el API."""
    member = next(case for case in cases if case.name == "permitido_empresa")
    for status in ("ACTIVE", "INACTIVE"):
        expected = _expected_branches(owner_url, member.company_id, status)
        observed = asyncio.run(contract(reader, member.subject, READ, BRANCHES).branches(member.company_id, status=status))
        assert observed == asyncio.run(_http_branches(expected).branches(member.company_id, status=status)) == expected
    assert _expected_branches(owner_url, member.company_id, "ACTIVE")


def test_branches_hidden_like_403_and_404(reader, cases):
    member = next(case for case in cases if case.name == "permitido_empresa")
    foreign = next(case for case in cases if case.name == "empresa_ajena")
    # Sin `branches:read` → [] (403 de hoy); usuario ajeno a la empresa → [] (404 de hoy).
    assert asyncio.run(contract(reader, member.subject, READ).branches(member.company_id, status="ACTIVE")) == []
    assert asyncio.run(contract(reader, foreign.subject, READ, BRANCHES).branches(foreign.company_id, status="ACTIVE")) == []
    assert asyncio.run(http(lambda request: httpx.Response(404)).branches(member.company_id, status="ACTIVE")) == []


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
