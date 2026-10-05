"""Reglas de precios de lista con reloj de base inyectado (T050; FR-050 a FR-054a; DS-08, DS-10; I2; H-04)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from commercial_relationship_service.application.exceptions import (
    CompanyProductInactiveError,
    InvalidStatusTransitionError,
    PresentationNotSellableError,
    PriceInEffectNotModifiableError,
    PriceListInactiveError,
    PriceListNotFoundError,
)
from commercial_relationship_service.application.price_list_item_service import PriceListItemService
from commercial_relationship_service.domain.errors import (
    PriceChangeOutOfPeriodError,
    PriceScaleNotAllowedError,
    ValidityInvalidError,
)

COMPANY = uuid4()
NOW = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)
DAY = timedelta(days=1)


class ById:
    def __init__(self, *rows) -> None:
        self.rows = {row.id: row for row in rows}

    def get(self, entity_id):
        return self.rows.get(entity_id)


class ItemsStub:
    duplicates: dict = {}

    def __init__(self) -> None:
        self.events: list[str] = []
        self.model = None
        self.change = None

    def database_now(self):
        return NOW

    def release(self):
        self.events.append("release")

    def build(self, **fields):
        return SimpleNamespace(**{"id": uuid4(), "status": "ACTIVE", "version": 1, **fields})

    def add(self, model, *, duplicates):
        self.events.append("add")
        self.model = model
        return model

    def load_for_update(self, entity_id, *, expected_version):
        self.events.append("load_for_update")
        return self.model

    def save(self, model, *, duplicates):
        self.events.append("save")
        return model

    def save_change(self, previous, new):
        self.events.append("save_change")
        self.change = (previous, new)


def _row(**fields):
    return SimpleNamespace(**{"id": uuid4(), "company_id": COMPANY, "status": "ACTIVE", **fields})


@pytest.fixture
def world():
    price_list = _row(currency_code="CLP")
    product = _row()
    presentation = _row(company_product_id=product.id, is_sellable=True)
    repository = ItemsStub()
    service = PriceListItemService(repository, ById(price_list), ById(product), ById(presentation))
    return SimpleNamespace(price_list=price_list, product=product, presentation=presentation,
                           repository=repository, service=service)


def _values(world, **overrides):
    values = {
        "price_list_id": world.price_list.id,
        "company_product_id": world.product.id,
        "company_product_presentation_id": None,
        "unit_price": Decimal("15000"),
        "valid_from": None,
        "valid_to": None,
    }
    values.update(overrides)
    return values


def _item(world, valid_from, valid_to=None, unit_price=Decimal("15000"), status="ACTIVE"):
    item = world.repository.build(
        company_id=COMPANY, price_list_id=world.price_list.id, company_product_id=world.product.id,
        company_product_presentation_id=None, unit_price=unit_price, valid_from=valid_from, valid_to=valid_to,
    )
    item.status = status
    world.repository.model = item
    return item


def test_create_defaults_to_server_time_and_list_currency_scale(world):
    model = world.service.create(COMPANY, _values(world), actor="sub")
    assert model.valid_from == NOW

    with pytest.raises(PriceScaleNotAllowedError):  # CLP: sin decimales (aclaración 5)
        world.service.create(COMPANY, _values(world, unit_price=Decimal("15000.5")), actor="sub")


def test_create_reference_checks(world):
    with pytest.raises(PriceListNotFoundError):
        world.service.create(COMPANY, _values(world, price_list_id=uuid4()), actor="sub")

    world.price_list.status = "INACTIVE"
    with pytest.raises(PriceListInactiveError):
        world.service.create(COMPANY, _values(world), actor="sub")

    world.price_list.status = "ACTIVE"
    world.product.status = "INACTIVE"
    with pytest.raises(CompanyProductInactiveError):
        world.service.create(COMPANY, _values(world), actor="sub")

    world.product.status = "ACTIVE"
    world.presentation.is_sellable = False
    with pytest.raises(PresentationNotSellableError):
        world.service.create(COMPANY, _values(world, company_product_presentation_id=world.presentation.id), actor="sub")


def test_future_price_is_fully_editable(world):
    current = _item(world, NOW + DAY)
    updated = world.service.update(
        current, {"unit_price": Decimal("16000"), "valid_from": NOW + 2 * DAY, "valid_to": None}, version=1, actor="sub"
    )
    assert (updated.unit_price, updated.valid_from) == (Decimal("16000"), NOW + 2 * DAY)


def test_in_effect_price_only_accepts_future_valid_to_including_postponing(world):
    current = _item(world, NOW - DAY, NOW + DAY)

    for values in (
        {"unit_price": Decimal("16000"), "valid_from": current.valid_from, "valid_to": current.valid_to},
        {"unit_price": current.unit_price, "valid_from": NOW - 2 * DAY, "valid_to": current.valid_to},
    ):
        with pytest.raises(PriceInEffectNotModifiableError):
            world.service.update(current, values, version=1, actor="sub")

    with pytest.raises(ValidityInvalidError):
        world.service.update(current, {"unit_price": current.unit_price, "valid_from": current.valid_from,
                                       "valid_to": NOW - DAY / 2}, version=1, actor="sub")

    postponed = world.service.update(current, {"unit_price": current.unit_price, "valid_from": current.valid_from,
                                               "valid_to": NOW + 30 * DAY}, version=1, actor="sub")
    assert postponed.valid_to == NOW + 30 * DAY  # I2: posponer se permite


def test_change_price_closes_previous_and_creates_new_atomically(world):
    current = _item(world, NOW - DAY, NOW + 10 * DAY)

    new, previous = world.service.change_price(
        current, unit_price=Decimal("16000"), effective_from=NOW + DAY, version=1, actor="sub"
    )

    assert world.repository.events[-1] == "save_change"
    assert previous.valid_to == NOW + DAY
    assert (new.valid_from, new.valid_to, new.unit_price) == (NOW + DAY, NOW + 10 * DAY, Decimal("16000"))


def test_change_price_defaults_to_now_and_rejects_out_of_period(world):
    current = _item(world, NOW - DAY)
    new, previous = world.service.change_price(current, unit_price=Decimal("1"), effective_from=None, version=1, actor="sub")
    assert new.valid_from == NOW == previous.valid_to

    current = _item(world, NOW - DAY, NOW + DAY)
    for effective in (NOW - DAY / 2, NOW + DAY):
        with pytest.raises(PriceChangeOutOfPeriodError):
            world.service.change_price(current, unit_price=Decimal("1"), effective_from=effective, version=1, actor="sub")


def test_h04_change_price_on_inactive_price_is_invalid_transition(world):
    current = _item(world, NOW - DAY, status="INACTIVE")
    with pytest.raises(InvalidStatusTransitionError):
        world.service.change_price(current, unit_price=Decimal("1"), effective_from=None, version=1, actor="sub")
