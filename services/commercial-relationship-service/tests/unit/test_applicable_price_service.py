"""Tabla de resolución del precio aplicable (T061; FR-055; aclaración 2; H-03)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from commercial_relationship_service.application.applicable_price_service import (
    ApplicablePriceService,
    PriceLine,
)
from commercial_relationship_service.application.exceptions import BatchLimitExceededError

COMPANY = uuid4()
AT = datetime(2026, 10, 5, 12, tzinfo=UTC)
DAY = timedelta(days=1)


def _row(**fields):
    return SimpleNamespace(**{"id": uuid4(), "status": "ACTIVE", **fields})


class Data:
    """Repositorio de resolución en memoria (misma forma que `resolution_data`)."""

    def __init__(self) -> None:
        self.product = _row(currency_code="COP", sale_price=Decimal("12000"))
        self.presentation = _row(company_product_id=self.product.id)
        self.default = _row(currency_code="COP", is_default=True, valid_from=None, valid_to=None)
        self.explicit = _row(currency_code="USD", is_default=False, valid_from=None, valid_to=None)
        self.items = {}
        self.calls = 0

    def price(self, price_list, presentation=None, unit_price="15000"):
        item = _row(unit_price=Decimal(unit_price))
        key = (price_list.id, self.product.id, None if presentation is None else presentation.id)
        self.items[key] = item
        return item

    def database_now(self):
        return AT

    def release(self):
        pass

    def resolution_data(self, company_id, *, product_ids, presentation_ids, list_ids, at):
        self.calls += 1
        products = {self.product.id: self.product} if self.product.id in product_ids else {}
        presentations = (
            {self.presentation.id: self.presentation}
            if self.presentation.id in presentation_ids and self.presentation.company_product_id in products
            else {}
        )
        lists = {row.id: row for row in (self.default, self.explicit)}
        return products, presentations, lists, self.items


@pytest.fixture
def data():
    return Data()


def _resolve(data, *lines, at=AT):
    return ApplicablePriceService(data).resolve(COMPANY, list(lines), at=at)[1]


def test_presentation_price_then_base_unit_price(data):
    by_presentation = data.price(data.default, data.presentation, "170000")
    general = data.price(data.default, None, "15000")

    with_presentation, without = _resolve(
        data,
        PriceLine(data.product.id, data.presentation.id, line_id="1"),
        PriceLine(data.product.id, line_id="2"),
    )

    assert (with_presentation.resolution, with_presentation.basis, with_presentation.price_list_item_id) == (
        "PRICE_LIST_ITEM", "PRESENTATION", by_presentation.id)
    assert (without.resolution, without.basis, without.price_list_item_id) == ("PRICE_LIST_ITEM", "BASE_UNIT", general.id)
    assert without.currency_code == "COP" and with_presentation.line_id == "1"
    assert data.calls == 1  # una sola consulta de datos por lote


def test_general_price_used_when_presentation_has_none(data):
    data.price(data.default, None, "15000")
    [line] = _resolve(data, PriceLine(data.product.id, data.presentation.id))
    assert (line.resolution, line.basis, line.unit_price) == ("PRICE_LIST_ITEM", "BASE_UNIT", Decimal("15000"))


def test_fallback_to_sale_price_only_without_explicit_list(data):
    [implicit] = _resolve(data, PriceLine(data.product.id))
    assert (implicit.resolution, implicit.unit_price, implicit.currency_code) == (
        "COMPANY_PRODUCT_SALE_PRICE", Decimal("12000"), "COP")

    [explicit] = _resolve(data, PriceLine(data.product.id, price_list_id=data.explicit.id))
    assert explicit.resolution == "NO_PRICE_IN_LIST" and explicit.unit_price is None  # aclaración 2


def test_no_default_list_falls_back(data):
    data.default.is_default = False
    [line] = _resolve(data, PriceLine(data.product.id))
    assert line.resolution == "COMPANY_PRODUCT_SALE_PRICE"


@pytest.mark.parametrize(
    "mutate",
    [
        lambda row: setattr(row, "status", "INACTIVE"),
        lambda row: setattr(row, "valid_to", AT),
        lambda row: setattr(row, "valid_from", AT + DAY),
    ],
)
def test_explicit_list_not_applicable(data, mutate):
    mutate(data.explicit)
    [line] = _resolve(data, PriceLine(data.product.id, price_list_id=data.explicit.id))
    assert line.resolution == "PRICE_LIST_NOT_APPLICABLE" and line.found is True


def test_explicit_list_of_other_company_or_missing(data):
    [line] = _resolve(data, PriceLine(data.product.id, price_list_id=uuid4()))
    assert line.resolution == "PRICE_LIST_NOT_APPLICABLE"


def test_not_found_product_presentation_and_h03(data):
    other_product_presentation = uuid4()
    lines = _resolve(
        data,
        PriceLine(uuid4()),
        PriceLine(data.product.id, other_product_presentation),
    )
    assert [(line.found, line.resolution) for line in lines] == [(False, "NOT_FOUND"), (False, "NOT_FOUND")]


def test_default_list_out_of_validity_is_ignored(data):
    data.price(data.default)
    data.default.valid_to = AT
    [line] = _resolve(data, PriceLine(data.product.id))
    assert line.resolution == "COMPANY_PRODUCT_SALE_PRICE"


def test_statuses_reported_and_batch_limit(data):
    data.product.status = "INACTIVE"
    [line] = _resolve(data, PriceLine(data.product.id, data.presentation.id))
    assert (line.company_product_status, line.presentation_status) == ("INACTIVE", "ACTIVE")

    with pytest.raises(BatchLimitExceededError):
        _resolve(data, *[PriceLine(data.product.id)] * 101)


def test_at_defaults_to_database_now(data):
    at, _ = ApplicablePriceService(data).resolve(COMPANY, [PriceLine(data.product.id)], at=None)
    assert at == AT
