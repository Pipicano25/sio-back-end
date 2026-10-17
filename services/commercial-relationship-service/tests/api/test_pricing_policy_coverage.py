"""Cobertura de políticas por presentación (spec 021, FR-021-35; `contracts/commercial-relationship.md` §3b; T094).

CP-71 (política inactiva), CP-72 (otra empresa), CP-73 (lista inactiva, vencida o de otra moneda), CP-74 (presentación
retirada), CP-75 (0 % configurado cubre). La respuesta no expone porcentajes, costos ni políticas (FR-021-32a).
Datos ficticios.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import text

from tests.api.automatic_pricing_helpers import add_presentation, policy, scenario
from tests.api.helpers import create_price_list
from tests.conftest import LOOKUP

COVERAGE = "perm:commercial-relationship:pricing_policy_coverage:read"
URL = "/api/v1/companies/{company}/pricing-policies/coverage"


@pytest.fixture
def supervisor(as_user):
    return as_user("supervisor.test")


@pytest.fixture
def admin(as_user):
    return as_user("admin.test")


@pytest.fixture
def purchase(as_token, service_token):
    """Identidad técnica de Purchase con el permiso nuevo y `platform:lookup` (sin membresía)."""
    return as_token(service_token(COVERAGE, LOOKUP, client_id="purchase-service"))


def ask(client, company, presentations, currency="COP", expect=200):
    response = client.post(URL.format(company=company), json={
        "currency_code": currency, "company_product_presentation_ids": [str(value) for value in presentations],
    })
    assert response.status_code == expect, response.text
    return response.json()


def by_id(body) -> dict[str, dict]:
    return {item["company_product_presentation_id"]: item for item in body["items"]}


def test_covered_and_not_covered_without_exposing_percentages(supervisor, purchase, company, fake_catalog) -> None:
    world = scenario(supervisor, company, fake_catalog)
    other = add_presentation(supervisor, company, fake_catalog, world)
    policy(supervisor, world, [world.presentation], markup="30")
    body = ask(purchase, company, [world.presentation, other, world.presentation])  # repetidos se ignoran
    assert [item["company_product_presentation_id"] for item in body["items"]] == [world.presentation, other]
    items = by_id(body)
    assert items[world.presentation] == {"company_product_presentation_id": world.presentation, "found": True,
                                         "covered": True, "price_list_ids": [world.price_list["id"]]}
    assert items[other] == {"company_product_presentation_id": other, "found": True, "covered": False, "price_list_ids": []}
    for forbidden in ("markup", "percentage", "policy", "cost", "price\""):
        assert forbidden not in str(body).replace("price_list_ids", "")


def test_cp75_zero_percent_covers_and_absence_is_not_zero(supervisor, purchase, company, fake_catalog) -> None:
    world = scenario(supervisor, company, fake_catalog)
    other = add_presentation(supervisor, company, fake_catalog, world)
    policy(supervisor, world, [world.presentation], markup="0")
    items = by_id(ask(purchase, company, [world.presentation, other]))
    assert items[world.presentation]["covered"] is True and items[other]["covered"] is False


def test_cp71_inactive_policy_does_not_cover(supervisor, admin, purchase, company, fake_catalog) -> None:
    world = scenario(supervisor, company, fake_catalog)
    created = policy(supervisor, world, [world.presentation])
    deactivated = admin.post(f"/api/v1/pricing-policies/{created['id']}/deactivate",
                             json={"version": created["version"], "reason": "Prueba de cobertura"})
    assert deactivated.status_code == 200, deactivated.text
    assert by_id(ask(purchase, company, [world.presentation]))[world.presentation]["covered"] is False


def test_cp74_removed_presentation_does_not_cover(supervisor, purchase, company, fake_catalog) -> None:
    world = scenario(supervisor, company, fake_catalog)
    created = policy(supervisor, world, [world.presentation])
    removed = supervisor.post(f"/api/v1/pricing-policies/{created['id']}/presentations/remove",
                              json={"version": created["version"], "company_product_presentation_ids": [world.presentation]})
    assert removed.status_code == 200, removed.text
    assert by_id(ask(purchase, company, [world.presentation]))[world.presentation]["covered"] is False


def test_percentage_change_keeps_coverage(supervisor, purchase, company, fake_catalog) -> None:
    """Cambiar el porcentaje cierra un término y abre otro: sigue cubierta (siempre hay término vigente)."""
    world = scenario(supervisor, company, fake_catalog)
    created = policy(supervisor, world, [world.presentation], markup="30")
    changed = supervisor.post(f"/api/v1/pricing-policies/{created['id']}/percentage",
                              json={"version": created["version"], "markup_percentage": "25"})
    assert changed.status_code == 200, changed.text
    assert by_id(ask(purchase, company, [world.presentation]))[world.presentation]["covered"] is True


def test_cp73_list_of_another_currency_inactive_or_expired_does_not_cover(supervisor, admin, purchase, company, fake_catalog, test_engine) -> None:
    usd = scenario(supervisor, company, fake_catalog, currency="USD")
    policy(supervisor, usd, [usd.presentation])
    assert by_id(ask(purchase, company, [usd.presentation]))[usd.presentation]["covered"] is False  # compra en COP
    assert by_id(ask(purchase, company, [usd.presentation], currency="USD"))[usd.presentation]["covered"] is True

    inactive = scenario(supervisor, company, fake_catalog)
    policy(supervisor, inactive, [inactive.presentation])
    deactivated = admin.post(f"/api/v1/price-lists/{inactive.price_list['id']}/deactivate",
                             json={"version": inactive.price_list["version"]})
    assert deactivated.status_code == 200, deactivated.text
    assert by_id(ask(purchase, company, [inactive.presentation]))[inactive.presentation]["covered"] is False

    expired = scenario(supervisor, company, fake_catalog)
    policy(supervisor, expired, [expired.presentation])
    with test_engine.begin() as connection:  # base aislada de pruebas: la lista venció
        connection.execute(text("UPDATE price_lists SET valid_from = now() - interval '2 days', "
                                "valid_to = now() - interval '1 day' WHERE id = :id"), {"id": expired.price_list["id"]})
    assert by_id(ask(purchase, company, [expired.presentation]))[expired.presentation]["covered"] is False


def test_covered_in_one_of_several_lists(supervisor, purchase, company, fake_catalog) -> None:
    """Basta una lista que la cubra; las demás pueden ser manuales o no incluirla (decisión 15)."""
    world = scenario(supervisor, company, fake_catalog)
    create_price_list(supervisor, company, code=f"MAN-{uuid4().hex[:4]}")  # lista manual, sin políticas
    second = create_price_list(supervisor, company, code=f"SEG-{uuid4().hex[:4]}")
    policy(supervisor, world, [world.presentation], price_list=second)
    item = by_id(ask(purchase, company, [world.presentation]))[world.presentation]
    assert item["covered"] is True and item["price_list_ids"] == [second["id"]]


def test_cp72_another_company_is_isolated(supervisor, purchase, company, fake_catalog, fake_oc) -> None:
    world = scenario(supervisor, company, fake_catalog)
    policy(supervisor, world, [world.presentation])
    other_company = uuid4()
    fake_oc.organizations[other_company] = uuid4()
    item = by_id(ask(purchase, other_company, [world.presentation]))[world.presentation]
    assert item == {"company_product_presentation_id": world.presentation, "found": False, "covered": False,
                    "price_list_ids": []}
    unknown = str(uuid4())
    assert by_id(ask(purchase, company, [unknown]))[unknown]["found"] is False


def test_authorization(as_token, as_user, service_token, company, fake_catalog, supervisor) -> None:
    world = scenario(supervisor, company, fake_catalog)
    url = URL.format(company=company)
    body = {"currency_code": "COP", "company_product_presentation_ids": [world.presentation]}
    assert as_token(None).post(url, json=body).status_code == 401
    # sin el permiso nuevo: 403 genérico (ni siquiera con platform:lookup)
    denied = as_token(service_token(LOOKUP, client_id="purchase-service")).post(url, json=body)
    assert denied.status_code == 403 and "pricing_policy_coverage" not in denied.text
    # el vendedor no consulta políticas (FR-021-32a)
    assert as_user("ventas.test").post(url, json=body).status_code == 403
    # identidad técnica sin platform:lookup ni membresía: 404 (no revela la empresa)
    assert as_token(service_token(COVERAGE, client_id="purchase-service")).post(url, json=body).status_code == 404
    # un supervisor miembro de la empresa sí puede consultarla
    assert as_user("supervisor.test").post(url, json=body).status_code == 200


def test_validation(purchase, company) -> None:
    url = URL.format(company=company)
    too_many = [str(uuid4()) for _ in range(101)]
    over = purchase.post(url, json={"currency_code": "COP", "company_product_presentation_ids": too_many})
    assert over.status_code == 422 and over.json()["code"] == "COMMERCIAL_RELATIONSHIP.BATCH_LIMIT_EXCEEDED"
    assert purchase.post(url, json={"currency_code": "COP", "company_product_presentation_ids": []}).status_code == 422
    assert purchase.post(url, json={"currency_code": "XXX", "company_product_presentation_ids": [str(uuid4())]}).status_code == 422
    assert purchase.post(url, json={"company_product_presentation_ids": [str(uuid4())]}).status_code == 422
