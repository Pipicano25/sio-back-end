"""Orden y cortocircuito de la adopción de presentaciones (T023; FR-011, FR-015; RC-07; H-01; DS-04, DS-05).

El alcance (paso 2) lo aplica la capa API; aquí se verifica el resto del orden:
entrada → producto del cuerpo → unicidades → elegibilidad → primer uso →
persistencia con retiro atómico de la marca anterior.
"""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from commercial_relationship_service.application.company_product_presentation_service import (
    CompanyProductPresentationService,
)
from commercial_relationship_service.application.exceptions import (
    CompanyProductInactiveError,
    CompanyProductNotFoundError,
    DependencyUnavailableError,
    DuplicateInternalCodeError,
    DuplicatePresentationAdoptionError,
    DuplicateSkuError,
    GlobalPresentationInactiveError,
    GlobalPresentationNotEligibleError,
    GlobalPresentationNotFoundError,
    GlobalPresentationOfOtherProductError,
    InvalidStatusTransitionError,
)
from commercial_relationship_service.domain.errors import DefaultFlagInvalidError
from tests.fakes import FakeProductCatalog

COMPANY = uuid4()


class ProductsStub:
    def __init__(self, product) -> None:
        self.product = product

    def get(self, entity_id):
        return self.product if self.product is not None and self.product.id == entity_id else None


class PresentationsStub:
    duplicates: dict = {}

    def __init__(self, *, adopted=False, taken: set[str] = frozenset()) -> None:
        self.adopted = adopted
        self.taken = taken
        self.events: list[str] = []
        self.model = None

    def adoption_exists(self, company_product_id, global_product_presentation_id):
        self.events.append("adoption_exists")
        return self.adopted

    def code_in_use(self, company_id, column, value, *, exclude_id=None):
        self.events.append(f"code_in_use:{column}")
        return column in self.taken and value is not None

    def build(self, **fields):
        return SimpleNamespace(id=uuid4(), **fields)

    def lock_product(self, company_product_id):
        self.events.append("lock_product")

    def clear_product_marks(self, mark, company_product_id, *, exclude_id, actor):
        self.events.append(f"clear:{mark}")

    def add(self, model, *, duplicates, audit=None):
        self.events.append("add")
        self.model = model
        return model

    def load_for_update(self, entity_id, *, expected_version):
        self.events.append("load_for_update")
        return self.model

    def save(self, model, *, duplicates, audit=None):
        self.events.append("save")
        return model


def _product(status="ACTIVE"):
    return SimpleNamespace(id=uuid4(), company_id=COMPANY, global_product_id=uuid4(), status=status)


def _values(product, presentation_id, **overrides):
    values = {
        "company_product_id": product.id,
        "global_product_presentation_id": presentation_id,
        "internal_code": None,
        "sku": "CJ12-001",
        "reference_code": None,
        "is_purchasable": True,
        "is_sellable": True,
        "is_default_purchase": False,
        "is_default_sale": False,
    }
    values.update(overrides)
    return values


def _setup(product=None, **repo):
    product = product or _product()
    catalog = FakeProductCatalog()
    presentation_id = catalog.add_presentation(uuid4(), product.global_product_id)
    repository = PresentationsStub(**repo)
    service = CompanyProductPresentationService(repository, ProductsStub(product), lambda: catalog)
    return service, repository, catalog, product, presentation_id


def test_adoption_order_and_first_use_with_presentation():
    service, repository, catalog, product, presentation_id = _setup()

    model = service.adopt(COMPANY, _values(product, presentation_id), actor="sub-admin")

    assert repository.events == [
        "adoption_exists", "code_in_use:sku", "code_in_use:internal_code", "lock_product", "add",
    ]
    assert catalog.presentation_lookup_calls == [presentation_id]
    assert catalog.presentation_first_use_calls == [(product.global_product_id, presentation_id)]
    assert model.created_by == model.updated_by == "sub-admin"


def test_default_mark_clears_previous_in_same_transaction():
    service, repository, _, product, presentation_id = _setup()

    service.adopt(COMPANY, _values(product, presentation_id, is_default_purchase=True), actor="sub")

    assert repository.events[-3:] == ["lock_product", "clear:is_default_purchase", "add"]


@pytest.mark.parametrize(
    ("product", "error"),
    [(None, CompanyProductNotFoundError), (_product("INACTIVE"), CompanyProductInactiveError)],
)
def test_product_of_body_must_exist_in_company_and_be_active(product, error):
    service, repository, catalog, _, presentation_id = _setup()
    service._products = ProductsStub(product)
    body_product = product or _product()

    with pytest.raises(error) as raised:
        service.adopt(COMPANY, _values(body_product, presentation_id), actor="sub")

    assert raised.value.field == "company_product_id"
    assert repository.events == [] and catalog.presentation_lookup_calls == []


def test_product_of_other_company_is_reported_as_not_found_h01():
    foreign = SimpleNamespace(id=uuid4(), company_id=uuid4(), global_product_id=uuid4(), status="ACTIVE")
    service, _, catalog, _, presentation_id = _setup(product=foreign)

    with pytest.raises(CompanyProductNotFoundError):
        service.adopt(COMPANY, _values(foreign, presentation_id), actor="sub")
    assert catalog.presentation_lookup_calls == []


@pytest.mark.parametrize(
    ("repo", "error"),
    [
        ({"adopted": True}, DuplicatePresentationAdoptionError),
        ({"taken": {"sku"}}, DuplicateSkuError),
        ({"taken": {"internal_code"}}, DuplicateInternalCodeError),
    ],
)
def test_local_uniqueness_stops_before_product_catalog(repo, error):
    service, _, catalog, product, presentation_id = _setup(**repo)

    with pytest.raises(error):
        service.adopt(COMPANY, _values(product, presentation_id, internal_code="INT-1"), actor="sub")

    assert catalog.presentation_lookup_calls == [] and catalog.presentation_first_use_calls == []


@pytest.mark.parametrize(
    ("mutate", "error"),
    [
        (lambda catalog, pid, product: catalog.presentations.pop(pid), GlobalPresentationNotFoundError),
        (lambda catalog, pid, product: catalog.add_presentation(pid, product.global_product_id, status="INACTIVE"), GlobalPresentationInactiveError),
        (lambda catalog, pid, product: catalog.add_presentation(pid, uuid4()), GlobalPresentationOfOtherProductError),
        (lambda catalog, pid, product: catalog.add_presentation(pid, product.global_product_id, eligible=False), GlobalPresentationNotEligibleError),
    ],
)
def test_eligibility_causes_never_register_first_use(mutate, error):
    service, repository, catalog, product, presentation_id = _setup()
    mutate(catalog, presentation_id, product)

    with pytest.raises(error) as raised:
        service.adopt(COMPANY, _values(product, presentation_id), actor="sub")

    assert raised.value.field == "global_product_presentation_id"
    assert catalog.presentation_first_use_calls == []
    assert "add" not in repository.events


@pytest.mark.parametrize("failure", ["unavailable", "not_eligible", "other_product"])
def test_first_use_failure_persists_nothing(failure):
    service, repository, catalog, product, presentation_id = _setup()
    catalog.first_use_error = failure

    with pytest.raises((DependencyUnavailableError, GlobalPresentationNotEligibleError, GlobalPresentationOfOtherProductError)):
        service.adopt(COMPANY, _values(product, presentation_id), actor="sub")

    assert "add" not in repository.events


def test_invalid_default_flags_are_input_errors():
    service, repository, catalog, product, presentation_id = _setup()

    with pytest.raises(DefaultFlagInvalidError):
        service.adopt(COMPANY, _values(product, presentation_id, is_purchasable=False, is_default_purchase=True), actor="sub")

    assert repository.events == [] and catalog.presentation_lookup_calls == []


def test_deactivate_clears_marks_and_reactivate_checks_product_and_presentation():
    service, repository, catalog, product, presentation_id = _setup()
    current = SimpleNamespace(
        id=uuid4(), company_id=COMPANY, company_product_id=product.id,
        global_product_presentation_id=presentation_id, status="ACTIVE",
        is_default_purchase=True, is_default_sale=True,
    )
    repository.model = current

    service.deactivate(current, version=1, actor="sub")
    assert (current.status, current.is_default_purchase, current.is_default_sale) == ("INACTIVE", False, False)

    service.reactivate(current, version=2, actor="sub")
    assert current.status == "ACTIVE"
    assert catalog.presentation_lookup_calls == [presentation_id]
    assert catalog.presentation_first_use_calls == []  # sin primer uso al reactivar

    current.status = "INACTIVE"
    catalog.add_presentation(presentation_id, product.global_product_id, status="INACTIVE")
    with pytest.raises(GlobalPresentationInactiveError):
        service.reactivate(current, version=3, actor="sub")

    product.status = "INACTIVE"
    with pytest.raises(CompanyProductInactiveError):
        service.reactivate(current, version=3, actor="sub")

    current.status = "ACTIVE"
    with pytest.raises(InvalidStatusTransitionError):
        service.reactivate(current, version=3, actor="sub")
