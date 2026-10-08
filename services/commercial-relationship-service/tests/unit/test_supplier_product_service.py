"""Reglas de productos de proveedor (T032; FR-021 a FR-027 sin cambios; I1; H-02; DS-07)."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from commercial_relationship_service.application.exceptions import (
    CompanyProductInactiveError,
    CompanyProductNotFoundError,
    CompanySupplierBlockedError,
    CompanySupplierInactiveError,
    CompanySupplierNotFoundError,
    DependencyUnavailableError,
    DuplicateSupplierProductError,
    PresentationInactiveError,
    PresentationNotFoundError,
    PresentationNotPurchasableError,
    PresentationOfOtherProductError,
    PurchaseUnitNotBaseUnitError,
)
from commercial_relationship_service.application.supplier_product_service import (
    SupplierProductService,
)
from tests.fakes import FakeProductCatalog

COMPANY = uuid4()


class ById:
    def __init__(self, *rows) -> None:
        self.rows = {row.id: row for row in rows}

    def get(self, entity_id):
        return self.rows.get(entity_id)


class SupplierProductsStub:
    duplicates: dict = {}

    def __init__(self, *, active_relation=False) -> None:
        self.active_relation = active_relation
        self.events: list[str] = []
        self.model = None

    def active_relation_exists(self, **kwargs):
        self.events.append("active_relation_exists")
        return self.active_relation

    def build(self, **fields):
        return SimpleNamespace(id=uuid4(), status="ACTIVE", version=1, **fields)

    def lock_product(self, company_product_id):
        self.events.append("lock_product")

    def clear_preferred(self, company_product_id, *, exclude_id, actor):
        self.events.append("clear_preferred")

    def add(self, model, *, duplicates, audit=None):
        self.events.append("add")
        self.model = model
        return model

    def load_for_update(self, entity_id, *, expected_version):
        return self.model

    def release(self):
        self.events.append("release")

    def save(self, model, *, duplicates, audit=None):
        self.events.append("save")
        return model


def _row(**fields):
    return SimpleNamespace(**{"id": uuid4(), "company_id": COMPANY, "status": "ACTIVE", **fields})


@pytest.fixture
def world():
    catalog = FakeProductCatalog()
    global_product = catalog.add(uuid4())
    product = _row(global_product_id=global_product)
    supplier = _row()
    presentation = _row(company_product_id=product.id, is_purchasable=True)
    repository = SupplierProductsStub()
    service = SupplierProductService(
        repository, ById(product), ById(supplier), ById(presentation), lambda: catalog
    )
    return SimpleNamespace(
        catalog=catalog, product=product, supplier=supplier, presentation=presentation,
        repository=repository, service=service, base_unit=catalog.base_units[global_product],
    )


def _values(world, **overrides):
    values = {
        "company_supplier_id": world.supplier.id,
        "company_product_id": world.product.id,
        "company_product_presentation_id": None,
        "supplier_product_code": None,
        "purchase_unit_id": world.base_unit,
        "minimum_order_quantity": Decimal("0"),
        "pack_quantity": Decimal("1"),
        "negotiated_unit_cost": Decimal("12500.5000"),
        "currency_code": "cop",
        "expected_supplier_lead_time_hours": None,
        "priority": None,
        "is_preferred": False,
    }
    values.update(overrides)
    return values


def test_create_valid_relation_normalizes_currency(world):
    model = world.service.create(COMPANY, _values(world), actor="sub")
    assert model.currency_code == "COP"
    assert world.repository.events == ["active_relation_exists", "add"]
    assert world.catalog.base_unit_calls == [world.product.global_product_id]


@pytest.mark.parametrize(
    ("status", "error"),
    [("INACTIVE", CompanySupplierInactiveError), ("BLOCKED", CompanySupplierBlockedError)],
)
def test_fr_021_unchanged_supplier_must_be_active_with_separate_causes(world, status, error):
    world.supplier.status = status

    with pytest.raises(error) as raised:
        world.service.create(COMPANY, _values(world), actor="sub")

    assert raised.value.field == "company_supplier_id"
    assert world.repository.events == []


def test_references_of_other_company_are_not_found(world):
    with pytest.raises(CompanySupplierNotFoundError):
        world.service.create(COMPANY, _values(world, company_supplier_id=uuid4()), actor="sub")

    world.product.company_id = uuid4()
    with pytest.raises(CompanyProductNotFoundError):
        world.service.create(COMPANY, _values(world), actor="sub")


def test_inactive_product(world):
    world.product.status = "INACTIVE"
    with pytest.raises(CompanyProductInactiveError):
        world.service.create(COMPANY, _values(world), actor="sub")


@pytest.mark.parametrize(
    ("mutate", "error"),
    [
        (lambda p, w: setattr(p, "company_product_id", uuid4()), PresentationOfOtherProductError),
        (lambda p, w: setattr(p, "status", "INACTIVE"), PresentationInactiveError),
        (lambda p, w: setattr(p, "is_purchasable", False), PresentationNotPurchasableError),
        (lambda p, w: setattr(p, "company_id", uuid4()), PresentationNotFoundError),
    ],
)
def test_presentation_checks(world, mutate, error):
    mutate(world.presentation, world)
    with pytest.raises(error):
        world.service.create(COMPANY, _values(world, company_product_presentation_id=world.presentation.id), actor="sub")


def test_purchase_unit_must_be_base_unit(world):
    with pytest.raises(PurchaseUnitNotBaseUnitError):
        world.service.create(COMPANY, _values(world, purchase_unit_id=uuid4()), actor="sub")

    world.catalog.base_units.clear()
    with pytest.raises(PurchaseUnitNotBaseUnitError):
        world.service.create(COMPANY, _values(world), actor="sub")

    world.catalog.base_unit_unavailable = True
    with pytest.raises(DependencyUnavailableError):
        world.service.create(COMPANY, _values(world), actor="sub")
    assert "add" not in world.repository.events


def test_duplicate_active_relation(world):
    world.repository.active_relation = True
    with pytest.raises(DuplicateSupplierProductError):
        world.service.create(COMPANY, _values(world), actor="sub")
    assert world.catalog.base_unit_calls == []


def test_preferred_mark_clears_previous(world):
    world.service.create(COMPANY, _values(world, is_preferred=True), actor="sub")
    assert world.repository.events == ["active_relation_exists", "lock_product", "clear_preferred", "add"]


def test_h02_update_revalidates_only_presentation_not_supplier(world):
    current = world.service.create(COMPANY, _values(world), actor="sub")
    current.version = 1
    world.supplier.status = "BLOCKED"  # no se revalida al modificar (FR-073, H-02)

    updated = world.service.update(
        current, _values(world, company_product_presentation_id=world.presentation.id), version=1, actor="sub"
    )
    assert updated.company_product_presentation_id == world.presentation.id
    assert world.catalog.base_unit_calls == [world.product.global_product_id]  # la unidad no cambió

    world.presentation.status = "INACTIVE"
    other = _row(company_product_id=world.product.id, is_purchasable=True, status="INACTIVE")
    world.service._presentations.rows[other.id] = other
    with pytest.raises(PresentationInactiveError):
        world.service.update(current, _values(world, company_product_presentation_id=other.id), version=1, actor="sub")


def test_update_checks_base_unit_only_when_unit_changes(world):
    current = world.service.create(COMPANY, _values(world), actor="sub")
    calls = len(world.catalog.base_unit_calls)

    world.service.update(current, _values(world, supplier_product_code="PRV-9"), version=1, actor="sub")
    assert len(world.catalog.base_unit_calls) == calls

    with pytest.raises(PurchaseUnitNotBaseUnitError):
        world.service.update(current, _values(world, purchase_unit_id=uuid4()), version=1, actor="sub")


def test_deactivate_clears_preferred_and_reactivate_rechecks(world):
    current = world.service.create(COMPANY, _values(world, is_preferred=True), actor="sub")
    current.status = "ACTIVE"

    world.service.deactivate(current, version=1, actor="sub")
    assert (current.status, current.is_preferred) == ("INACTIVE", False)

    world.supplier.status = "INACTIVE"
    with pytest.raises(CompanySupplierInactiveError):
        world.service.reactivate(current, version=2, actor="sub")

    world.supplier.status = "ACTIVE"
    world.repository.active_relation = True
    with pytest.raises(DuplicateSupplierProductError):
        world.service.reactivate(current, version=2, actor="sub")

    world.repository.active_relation = False
    calls = len(world.catalog.base_unit_calls)
    world.service.reactivate(current, version=2, actor="sub")
    assert current.status == "ACTIVE"
    assert len(world.catalog.base_unit_calls) == calls  # no vuelve a consultar la unidad base
