"""Auxiliares de las pruebas de actualización automática de precios (spec 021). Datos ficticios."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import text

from tests.api.helpers import adopt, adopt_presentation, create_price_list

SUBMIT = "perm:commercial-relationship:automatic_price_update_requests:submit"
REQUESTS = "/api/v1/companies/{company}/automatic-price-update-requests"


@dataclass
class Scenario:
    company: object
    product: dict
    presentation: str
    price_list: dict


def scenario(client, company, fake_catalog, *, currency: str = "COP") -> Scenario:
    product = adopt(client, company, fake_catalog, internal_code=f"AUT-{uuid4().hex[:6]}")
    presentation = adopt_presentation(client, company, fake_catalog, product)["id"]
    price_list = create_price_list(client, company, code=f"PUB-{uuid4().hex[:4]}", currency_code=currency)
    return Scenario(company, product, presentation, price_list)


def add_presentation(client, company, fake_catalog, world: Scenario) -> str:
    return adopt_presentation(client, company, fake_catalog, world.product)["id"]


def policy(client, world: Scenario, presentations, *, markup: str = "30", name: str | None = None, price_list=None) -> dict:
    target = price_list or world.price_list
    response = client.post(
        f"/api/v1/companies/{world.company}/price-lists/{target['id']}/pricing-policies",
        json={"name": name or f"Política {uuid4().hex[:4]}", "markup_percentage": markup,
              "company_product_presentation_ids": list(presentations)},
    )
    assert response.status_code == 201, response.text
    return response.json()


def request_body(
    world: Scenario,
    *,
    sequence: int = 1,
    line_total: str = "23800.00",
    quantity: str = "10.0000",
    previous: tuple[str, str] | None = None,
    presentation: str | None = None,
    received_at: datetime | None = None,
    currency: str = "COP",
    **overrides,
) -> dict:
    body = {
        "contract_version": 1,
        "purchase_detail_id": str(uuid4()),
        "purchase_id": str(uuid4()),
        "branch_id": str(uuid4()),
        "company_product_id": world.product["id"],
        "company_product_presentation_id": presentation or world.presentation,
        "sequence": sequence,
        "previous_sequence": sequence - 1 if sequence > 1 else None,
        "currency_code": currency,
        "line_total": line_total,
        "quantity": quantity,
        "previous_purchase_detail_id": str(uuid4()) if previous else None,
        "previous_line_total": previous[0] if previous else None,
        "previous_quantity": previous[1] if previous else None,
        "received_at": (received_at or datetime.now(UTC)).isoformat(),
        "received_by_user_id": str(uuid4()),
    }
    body.update(overrides)
    return body


def technical(as_token, service_token, *roles: str):
    return as_token(service_token(*(roles or (SUBMIT,)), client_id="purchase-service"))


def submit(client, world: Scenario, body: dict, expect: int = 202):
    response = client.post(REQUESTS.format(company=world.company), json=body)
    assert response.status_code == expect, response.text
    return response.json()


def run_worker(test_engine, *, until_idle: bool = True):
    """Ejecuta el worker de precios contra la base de pruebas hasta que no quede trabajo procesable."""
    from commercial_relationship_service.price_worker import run_cycle

    results = []
    while True:
        result = run_cycle(test_engine, batch_size=50, max_backoff_seconds=300, interval_seconds=0.01)
        results.append(result)
        if not until_idle or result.processed == 0:
            return results


def prices(test_engine, world: Scenario, presentation: str | None = None, price_list=None) -> list[dict]:
    with test_engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT id, unit_price, valid_from, valid_to, status, origin, closure_reason, automatic_application_id, "
                "version, updated_at "
                "FROM price_list_items WHERE price_list_id = :l AND company_product_presentation_id = :p "
                "ORDER BY valid_from, created_at"
            ),
            {"l": (price_list or world.price_list)["id"], "p": presentation or world.presentation},
        ).mappings()
        return [dict(row) for row in rows]


def current_price(test_engine, world: Scenario, presentation: str | None = None, price_list=None) -> Decimal | None:
    now = datetime.now(UTC)
    for row in prices(test_engine, world, presentation, price_list):
        if row["status"] == "ACTIVE" and row["valid_from"] <= now and (row["valid_to"] is None or row["valid_to"] > now):
            return row["unit_price"]
    return None


def applications(test_engine) -> list[dict]:
    with test_engine.connect() as connection:
        return [dict(row) for row in connection.execute(
            text("SELECT * FROM automatic_price_applications ORDER BY sequence, created_at")
        ).mappings()]
