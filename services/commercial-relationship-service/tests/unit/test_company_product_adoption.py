"""Orden y cortocircuito de la adopción (FR-010, FR-011, RC-05, DS-01).

El alcance (paso 2 de FR-011) lo aplica la capa API antes del servicio; aquí se
verifica el resto del orden: validaciones → unicidad local → elegibilidad →
primer uso → inserción.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest

from commercial_relationship_service.application.company_product_service import (
    CompanyProductService,
)
from commercial_relationship_service.application.exceptions import (
    DependencyUnavailableError,
    DuplicateAdoptionError,
    DuplicateInternalCodeError,
    GlobalProductInactiveError,
    GlobalProductNotEligibleError,
    GlobalProductNotFoundError,
)
from commercial_relationship_service.domain.errors import (
    CurrencyNotSupportedError,
    InventoryFlagsInvalidError,
    PriceScaleNotAllowedError,
)
from tests.fakes import FakeProductCatalog


class RepositoryStub:
    duplicates: dict = {}

    def __init__(self, *, adopted: bool = False, code_taken: bool = False) -> None:
        self.adopted = adopted
        self.taken = code_taken
        self.events: list[str] = []
        self.created: dict | None = None

    def adoption_exists(self, company_id, global_product_id):
        self.events.append("adoption_exists")
        return self.adopted

    def code_taken(self, company_id, internal_code, exclude_id=None):
        self.events.append("code_taken")
        return self.taken

    def create(self, **fields):
        self.events.append("create")
        self.created = fields
        return fields


def _values(product_id, **overrides):
    values = {
        "global_product_id": product_id,
        "internal_code": "000045",
        "reference_code": None,
        "display_name": "Producto",
        "short_name": None,
        "sale_price": Decimal("0"),
        "currency_code": "cop",
        "reference_cost": Decimal("0"),
        "inventory_control_enabled": True,
        "lot_tracking_enabled": False,
        "expiration_tracking_enabled": False,
        "is_purchasable": True,
        "is_sellable": True,
    }
    values.update(overrides)
    return values


def _service(repository, catalog):
    return CompanyProductService(repository, lambda: catalog)


def test_happy_path_order_and_defaults():
    catalog = FakeProductCatalog()
    product = catalog.add(uuid4())
    repository = RepositoryStub()

    created = _service(repository, catalog).adopt(uuid4(), _values(product), actor="sub-1")

    assert repository.events == ["adoption_exists", "code_taken", "create"]
    assert catalog.lookup_calls == [product]
    assert catalog.first_use_calls == [product]
    assert created["currency_code"] == "COP"
    assert created["created_by"] == created["updated_by"] == "sub-1"
    assert created["sale_price"] == Decimal("0") and created["reference_cost"] == Decimal("0")
    assert created["inventory_control_enabled"] and created["is_purchasable"] and created["is_sellable"]
    assert not created["lot_tracking_enabled"] and not created["expiration_tracking_enabled"]


@pytest.mark.parametrize(
    ("overrides", "error"),
    [
        ({"currency_code": "XYZ"}, CurrencyNotSupportedError),
        ({"currency_code": "CLP", "sale_price": Decimal("1500.50")}, PriceScaleNotAllowedError),
        ({"inventory_control_enabled": False, "lot_tracking_enabled": True}, InventoryFlagsInvalidError),
    ],
)
def test_validation_stops_before_anything_else(overrides, error):
    catalog = FakeProductCatalog()
    product = catalog.add(uuid4())
    repository = RepositoryStub()

    with pytest.raises(error):
        _service(repository, catalog).adopt(uuid4(), _values(product, **overrides), actor="s")

    assert repository.events == [] and catalog.lookup_calls == [] and catalog.first_use_calls == []


@pytest.mark.parametrize(
    ("repository", "error"),
    [
        (RepositoryStub(adopted=True), DuplicateAdoptionError),
        (RepositoryStub(code_taken=True), DuplicateInternalCodeError),
    ],
)
def test_local_uniqueness_does_not_call_product_catalog(repository, error):
    catalog = FakeProductCatalog()
    product = catalog.add(uuid4())

    with pytest.raises(error):
        _service(repository, catalog).adopt(uuid4(), _values(product), actor="s")

    assert catalog.lookup_calls == [] and catalog.first_use_calls == []
    assert "create" not in repository.events


@pytest.mark.parametrize(
    ("setup", "error"),
    [
        (lambda catalog, product: None, GlobalProductNotFoundError),
        (lambda catalog, product: catalog.add(product, status="INACTIVE"), GlobalProductInactiveError),
        (lambda catalog, product: catalog.add(product, eligible=False), GlobalProductNotEligibleError),
    ],
)
def test_eligibility_rejections_do_not_register_first_use(setup, error):
    catalog = FakeProductCatalog()
    product = uuid4()
    setup(catalog, product)
    repository = RepositoryStub()

    with pytest.raises(error) as raised:
        _service(repository, catalog).adopt(uuid4(), _values(product), actor="s")

    assert raised.value.field == "global_product_id"
    assert catalog.first_use_calls == []
    assert "create" not in repository.events


@pytest.mark.parametrize(
    ("failure", "error"),
    [
        ("not_eligible", GlobalProductNotEligibleError),
        ("not_found", GlobalProductNotFoundError),
        ("unavailable", DependencyUnavailableError),
    ],
)
def test_first_use_failure_never_inserts(failure, error):
    catalog = FakeProductCatalog(first_use_error=failure)
    product = catalog.add(uuid4())
    repository = RepositoryStub()

    with pytest.raises(error):
        _service(repository, catalog).adopt(uuid4(), _values(product), actor="s")

    assert catalog.first_use_calls == [product]
    assert "create" not in repository.events


def test_lookup_unavailable_is_503_without_first_use():
    catalog = FakeProductCatalog(lookup_unavailable=True)
    repository = RepositoryStub()

    with pytest.raises(DependencyUnavailableError):
        _service(repository, catalog).adopt(uuid4(), _values(uuid4()), actor="s")

    assert catalog.first_use_calls == []
