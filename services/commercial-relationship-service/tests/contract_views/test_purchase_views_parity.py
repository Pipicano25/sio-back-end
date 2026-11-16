"""Paridad de las vistas de contrato de Commercial Relationship para Purchase (spec 025, T050).

Para los mismos datos, cada columna de la vista coincide con el mismo campo de la respuesta que hoy lee Purchase
(``purchase_service/infrastructure/commercial_relationship_directory.py``):

- ``v1_company_suppliers`` ↔ ``GET /company-suppliers/{id}`` (``get_supplier``), incluidos ``BLOCKED`` e ``INACTIVE``;
- ``v1_supplier_payment_conditions`` ↔ ``GET /supplier-payment-conditions/{id}`` (``get_payment_condition``);
- ``v1_supplier_products`` ↔ ``GET /supplier-products/{id}`` (``get_supplier_product``);
- ``v1_pricing_coverage`` + ``v1_company_product_presentations`` con ``COVERAGE_SQL`` ↔
  ``POST /companies/{c}/pricing-policies/coverage`` (``lookup_pricing_coverage``): cubierta, sin cubrir, término
  vencido, política inactiva, presentación retirada, lista inactiva, lista vencida, otra moneda, presentación de otra
  empresa e inexistente (``found = false``).

Incluye filas de otra empresa: la vista tiene todas las empresas y el consumidor filtra por ``company_id``.
Datos ficticios.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import text

from tests.api.automatic_pricing_helpers import add_presentation, policy, scenario
from tests.api.helpers import adopt, adopt_presentation, create_condition, create_supplier_product, supplier
from tests.conftest import LOOKUP, user_sub

# Consulta de referencia del consumidor (Purchase la copia tal cual). Parámetros: ``company_id`` (uuid),
# ``currency_code`` (ISO 4217 ya validado) e ``ids`` (lista de uuid sin repetir, hasta 100). Devuelve una fila por id
# pedido, en el orden pedido: ``found`` = la presentación existe en la empresa (cualquier estado); ``covered`` = además
# hay al menos una lista de la empresa, en esa moneda, que la cubre ahora. ``price_list_ids`` va solo como
# diagnóstico (el endpoint lo devuelve ordenado como texto).
COVERAGE_SQL = """
SELECT r.id AS company_product_presentation_id,
       (p.id IS NOT NULL) AS found,
       (p.id IS NOT NULL AND EXISTS (
            SELECT 1
              FROM contract.v1_pricing_coverage c
             WHERE c.company_id = CAST(:company_id AS uuid)
               AND c.company_product_presentation_id = r.id
               AND c.currency_code = :currency_code
       )) AS covered
  FROM unnest(CAST(:ids AS uuid[])) WITH ORDINALITY AS r(id, position)
  LEFT JOIN contract.v1_company_product_presentations p
         ON p.id = r.id AND p.company_id = CAST(:company_id AS uuid)
 ORDER BY r.position
"""

PRICE_LISTS_SQL = """
SELECT company_product_presentation_id, price_list_id
  FROM contract.v1_pricing_coverage
 WHERE company_id = CAST(:company_id AS uuid)
   AND currency_code = :currency_code
   AND company_product_presentation_id = ANY(CAST(:ids AS uuid[]))
"""

SUPPLIER_COLUMNS = ("id", "company_id", "organization_identity_id", "display_name", "status")
CONDITION_COLUMNS = (
    "id", "company_id", "company_supplier_id", "payment_condition_type_id", "currency_code", "payment_terms_days",
    "valid_from", "valid_to", "status",
)
SUPPLIER_PRODUCT_COLUMNS = (
    "id", "company_id", "company_supplier_id", "company_product_id", "company_product_presentation_id",
    "expected_supplier_lead_time_hours", "status",
)
COVERAGE = "perm:commercial-relationship:pricing_policy_coverage:read"
COVERAGE_URL = "/api/v1/companies/{company}/pricing-policies/coverage"


def _norm(column: str, value: Any) -> Any:
    """Lleva el valor de la vista y el de la respuesta JSON a la misma forma."""
    if value is None or isinstance(value, bool | int):
        return value
    if column == "expected_supplier_lead_time_hours":
        return Decimal(str(value))
    if column in ("valid_from", "valid_to"):
        return value if isinstance(value, datetime) else datetime.fromisoformat(value)
    return str(value)


def _assert_same(view: dict[str, Any], body: dict[str, Any], columns: tuple[str, ...]) -> None:
    for column in columns:
        assert _norm(column, view[column]) == _norm(column, body[column]), column


def _view_rows(connection, view: str, ids: list[str]) -> dict[str, dict[str, Any]]:
    rows = connection.execute(
        text(f"SELECT * FROM contract.{view} WHERE id = ANY(CAST(:ids AS uuid[]))"), {"ids": ids}
    ).mappings().all()
    return {str(row["id"]): dict(row) for row in rows}


@pytest.fixture
def admin(as_user, fake_oc, other_company):
    """`admin.test`, miembro de las dos empresas para poder preparar datos en ambas."""
    fake_oc.add_member(user_sub("admin.test"), other_company)
    return as_user("admin.test")


@pytest.fixture
def technical(as_token, service_token):
    """Identidad técnica de Purchase: lectura de cada recurso y cobertura con `platform:lookup` (sin membresía)."""
    return as_token(service_token(
        "perm:commercial-relationship:company_suppliers:read",
        "perm:commercial-relationship:supplier_payment_conditions:read",
        "perm:commercial-relationship:supplier_products:read",
        COVERAGE,
        LOOKUP,
        client_id="purchase-service",
    ))


def _act(client, path: str, action: str, **body: Any) -> dict[str, Any]:
    version = client.get(path).json()["version"]
    response = client.post(f"{path}/{action}", json={"version": version, **body})
    assert response.status_code == 200, response.text
    return response.json()


def test_company_suppliers_match_get(admin, technical, company, other_company, fake_party, test_engine):
    active = supplier(admin, company, fake_party, internal_code="PRV-1", display_name="Proveedor activo")
    blocked = supplier(admin, company, fake_party, internal_code="PRV-2")
    _act(admin, f"/api/v1/company-suppliers/{blocked['id']}", "block", block_reason="Incumplimiento")
    inactive = supplier(admin, company, fake_party, internal_code="PRV-3")
    _act(admin, f"/api/v1/company-suppliers/{inactive['id']}", "deactivate")
    foreign = supplier(admin, other_company, fake_party, internal_code="PRV-1",
                       organization_identity_id=active["organization_identity_id"], display_name="En otra")

    suppliers = (active, blocked, inactive, foreign)
    with test_engine.connect() as connection:
        views = _view_rows(connection, "v1_company_suppliers", [item["id"] for item in suppliers])
        assert sorted(views) == sorted(item["id"] for item in suppliers)
        for item in suppliers:
            response = technical.get(f"/api/v1/company-suppliers/{item['id']}")
            assert response.status_code == 200, response.text
            _assert_same(views[item["id"]], response.json(), SUPPLIER_COLUMNS)
        assert {views[item["id"]]["status"] for item in suppliers} == {"ACTIVE", "BLOCKED", "INACTIVE"}
        assert str(views[foreign["id"]]["company_id"]) == str(other_company)
        missing = connection.execute(text("SELECT count(*) FROM contract.v1_company_suppliers WHERE id = :id"),
                                     {"id": str(uuid4())}).scalar_one()
        assert missing == 0  # el GET devolvería 404 → None


def test_supplier_payment_conditions_match_get(
    admin, technical, company, other_company, fake_party, fake_payment, test_engine
):
    provider = supplier(admin, company, fake_party)
    until = (datetime.now(UTC) + timedelta(days=30)).isoformat()
    credit = create_condition(admin, company, provider, fake_payment, valid_to=until)
    cash = create_condition(admin, company, provider, fake_payment, code="CASH", currency_code="USD")
    _act(admin, f"/api/v1/supplier-payment-conditions/{cash['id']}", "deactivate")
    foreign_provider = supplier(admin, other_company, fake_party)
    foreign = create_condition(admin, other_company, foreign_provider, fake_payment)

    conditions = (credit, cash, foreign)
    with test_engine.connect() as connection:
        views = _view_rows(connection, "v1_supplier_payment_conditions", [item["id"] for item in conditions])
        assert sorted(views) == sorted(item["id"] for item in conditions)
        for item in conditions:
            response = technical.get(f"/api/v1/supplier-payment-conditions/{item['id']}")
            assert response.status_code == 200, response.text
            _assert_same(views[item["id"]], response.json(), CONDITION_COLUMNS)
        assert views[credit["id"]]["valid_to"] is not None and views[cash["id"]]["status"] == "INACTIVE"
        assert views[credit["id"]]["payment_terms_days"] == 30


def test_supplier_products_match_get(admin, technical, company, other_company, fake_party, fake_catalog, test_engine):
    provider = supplier(admin, company, fake_party)
    product = adopt(admin, company, fake_catalog, internal_code="SP-1")
    presentation = adopt_presentation(admin, company, fake_catalog, product)
    general = create_supplier_product(admin, company, provider, product, fake_catalog,
                                      expected_supplier_lead_time_hours="36.5")
    specific = create_supplier_product(admin, company, provider, product, fake_catalog,
                                       company_product_presentation_id=presentation["id"])
    _act(admin, f"/api/v1/supplier-products/{specific['id']}", "deactivate")
    foreign_provider = supplier(admin, other_company, fake_party)
    foreign_product = adopt(admin, other_company, fake_catalog, internal_code="SP-1")
    foreign = create_supplier_product(admin, other_company, foreign_provider, foreign_product, fake_catalog,
                                      expected_supplier_lead_time_hours="48")

    rows = (general, specific, foreign)
    with test_engine.connect() as connection:
        views = _view_rows(connection, "v1_supplier_products", [item["id"] for item in rows])
        assert sorted(views) == sorted(item["id"] for item in rows)
        for item in rows:
            response = technical.get(f"/api/v1/supplier-products/{item['id']}")
            assert response.status_code == 200, response.text
            _assert_same(views[item["id"]], response.json(), SUPPLIER_PRODUCT_COLUMNS)
        assert views[general["id"]]["expected_supplier_lead_time_hours"] == Decimal("36.5")
        assert views[general["id"]]["company_product_presentation_id"] is None
        assert str(views[specific["id"]]["company_product_presentation_id"]) == presentation["id"]
        assert views[specific["id"]]["status"] == "INACTIVE"


def _endpoint(client, company, currency: str, ids: list[str]) -> list[dict[str, Any]]:
    response = client.post(COVERAGE_URL.format(company=company),
                           json={"currency_code": currency, "company_product_presentation_ids": ids})
    assert response.status_code == 200, response.text
    return response.json()["items"]


def _consumer(connection, company, currency: str, ids: list[str]) -> list[dict[str, Any]]:
    params = {"company_id": str(company), "currency_code": currency, "ids": ids}
    rows = connection.execute(text(COVERAGE_SQL), params).mappings().all()
    lists: dict[str, list[str]] = {}
    for presentation_id, price_list_id in connection.execute(text(PRICE_LISTS_SQL), params).all():
        lists.setdefault(str(presentation_id), []).append(str(price_list_id))
    return [
        {
            "company_product_presentation_id": str(row["company_product_presentation_id"]),
            "found": row["found"],
            "covered": row["covered"],
            "price_list_ids": sorted(lists.get(str(row["company_product_presentation_id"]), [])) if row["found"] else [],
        }
        for row in rows
    ]


def test_pricing_coverage_matches_endpoint(admin, technical, company, other_company, fake_catalog, test_engine):
    covered = scenario(admin, company, fake_catalog)
    policy(admin, covered, [covered.presentation])
    uncovered = add_presentation(admin, company, fake_catalog, covered)
    # Cubierta en dos listas COP (una de ellas, la del escenario).
    twice = add_presentation(admin, company, fake_catalog, covered)
    policy(admin, covered, [twice])
    second = scenario(admin, company, fake_catalog)
    policy(admin, second, [twice], price_list=second.price_list)

    expired_term = scenario(admin, company, fake_catalog)
    expired_policy = policy(admin, expired_term, [expired_term.presentation])
    with test_engine.begin() as connection:  # base aislada: el término de porcentaje venció (solo se cierra)
        connection.execute(text(
            "UPDATE price_list_pricing_policy_terms SET valid_to = valid_from + interval '1 microsecond', "
            "closed_at = now(), closed_by = 'prueba' WHERE policy_id = :p AND valid_to IS NULL"
        ), {"p": expired_policy["id"]})

    inactive_policy = scenario(admin, company, fake_catalog)
    created = policy(admin, inactive_policy, [inactive_policy.presentation])
    response = admin.post(f"/api/v1/pricing-policies/{created['id']}/deactivate",
                          json={"version": created["version"], "reason": "Prueba de vista"})
    assert response.status_code == 200, response.text

    removed = scenario(admin, company, fake_catalog)
    created = policy(admin, removed, [removed.presentation])
    response = admin.post(f"/api/v1/pricing-policies/{created['id']}/presentations/remove",
                          json={"version": created["version"], "company_product_presentation_ids": [removed.presentation]})
    assert response.status_code == 200, response.text

    inactive_list = scenario(admin, company, fake_catalog)
    policy(admin, inactive_list, [inactive_list.presentation])
    _act(admin, f"/api/v1/price-lists/{inactive_list.price_list['id']}", "deactivate")

    expired_list = scenario(admin, company, fake_catalog)
    policy(admin, expired_list, [expired_list.presentation])
    with test_engine.begin() as connection:
        connection.execute(text("UPDATE price_lists SET valid_from = now() - interval '2 days', "
                                "valid_to = now() - interval '1 day' WHERE id = :id"),
                           {"id": expired_list.price_list["id"]})

    usd = scenario(admin, company, fake_catalog, currency="USD")
    policy(admin, usd, [usd.presentation])

    foreign = scenario(admin, other_company, fake_catalog)
    policy(admin, foreign, [foreign.presentation])

    ids = [covered.presentation, uncovered, twice, expired_term.presentation, inactive_policy.presentation,
           removed.presentation, inactive_list.presentation, expired_list.presentation, usd.presentation,
           foreign.presentation, str(uuid4())]

    with test_engine.connect() as connection:
        cases = {}
        for target, currency in ((company, "COP"), (company, "USD"), (other_company, "COP"), (other_company, "USD")):
            expected = _endpoint(technical, target, currency, ids)
            actual = _consumer(connection, target, currency, ids)
            assert actual == expected, (target, currency)
            cases[(target, currency)] = {item["company_product_presentation_id"]: item for item in actual}

    cop = cases[(company, "COP")]
    assert {key for key, item in cop.items() if item["covered"]} == {covered.presentation, twice}
    assert sorted(cop[twice]["price_list_ids"]) == sorted([covered.price_list["id"], second.price_list["id"]])
    for key in (uncovered, expired_term.presentation, inactive_policy.presentation, removed.presentation,
                inactive_list.presentation, expired_list.presentation, usd.presentation):
        assert cop[key]["found"] is True and cop[key]["covered"] is False, key
    assert cop[foreign.presentation]["found"] is False and cop[ids[-1]]["found"] is False
    assert {key for key, item in cases[(company, "USD")].items() if item["covered"]} == {usd.presentation}
    other = cases[(other_company, "COP")]
    assert {key for key, item in other.items() if item["found"]} == {foreign.presentation}
    assert other[foreign.presentation]["covered"] is True
    assert not any(item["covered"] for item in cases[(other_company, "USD")].values())


def test_pricing_coverage_hides_percentages(test_engine) -> None:
    with test_engine.connect() as connection:
        columns = list(connection.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'contract' AND table_name = 'v1_pricing_coverage' ORDER BY ordinal_position"
        )).scalars())
    assert columns == ["company_id", "company_product_presentation_id", "price_list_id", "currency_code"]
