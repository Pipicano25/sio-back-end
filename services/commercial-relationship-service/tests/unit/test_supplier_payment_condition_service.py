"""Reglas de condiciones de pago (T041; FR-031 sin cambios; FR-032, FR-033; DS-06; I1)."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from commercial_relationship_service.application.exceptions import (
    CompanySupplierBlockedError,
    CompanySupplierInactiveError,
    DependencyUnavailableError,
    PaymentConditionTypeInactiveError,
    PaymentConditionTypeNotFoundError,
)
from commercial_relationship_service.application.supplier_payment_condition_service import (
    SupplierPaymentConditionService,
)
from commercial_relationship_service.domain.errors import PaymentTermsInconsistentError
from tests.fakes import FakePaymentReference

COMPANY = uuid4()
NOW = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)


class Suppliers:
    def __init__(self, supplier) -> None:
        self.supplier = supplier

    def get(self, entity_id):
        return self.supplier if self.supplier.id == entity_id else None


class ConditionsStub:
    duplicates: dict = {}

    def __init__(self) -> None:
        self.events: list[str] = []
        self.model = None

    def database_now(self):
        return NOW

    def release(self):
        self.events.append("release")

    def build(self, **fields):
        return SimpleNamespace(id=uuid4(), status="ACTIVE", version=1, **fields)

    def lock_supplier(self, company_supplier_id):
        self.events.append("lock_supplier")

    def clear_default(self, company_supplier_id, currency_code, *, exclude_id, actor):
        self.events.append(f"clear_default:{currency_code}")

    def add(self, model, *, duplicates, audit=None):
        self.events.append("add")
        self.model = model
        return model

    def load_for_update(self, entity_id, *, expected_version):
        return self.model

    def save(self, model, *, duplicates, audit=None):
        self.events.append("save")
        return model


@pytest.fixture
def world():
    payment = FakePaymentReference()
    supplier = SimpleNamespace(id=uuid4(), company_id=COMPANY, status="ACTIVE")
    repository = ConditionsStub()
    service = SupplierPaymentConditionService(repository, Suppliers(supplier), lambda: payment)
    return SimpleNamespace(payment=payment, supplier=supplier, repository=repository, service=service)


def _values(world, code="CREDIT", **overrides):
    values = {
        "company_supplier_id": world.supplier.id,
        "payment_condition_type_id": overrides.pop("payment_condition_type_id", None) or world.payment.id_of(code),
        "currency_code": "cop",
        "payment_terms_days": 0 if code == "CASH" else 30,
        "credit_limit": None,
        "interest_rate_percentage": None,
        "cash_discount_percentage": None,
        "is_default": False,
        "valid_from": None,
        "valid_to": None,
    }
    values.update(overrides)
    return values


def test_create_uses_server_time_and_normalized_currency(world):
    model = world.service.create(COMPANY, _values(world), actor="sub")
    assert model.valid_from == NOW and model.currency_code == "COP"
    assert world.repository.events == ["release", "add"]


@pytest.mark.parametrize(("status", "error"), [("INACTIVE", CompanySupplierInactiveError), ("BLOCKED", CompanySupplierBlockedError)])
def test_fr_031_unchanged_supplier_must_be_active(world, status, error):
    world.supplier.status = status
    with pytest.raises(error):
        world.service.create(COMPANY, _values(world), actor="sub")
    assert world.payment.calls == []


def test_condition_type_not_found_inactive_and_unavailable(world):
    with pytest.raises(PaymentConditionTypeNotFoundError):
        world.service.create(COMPANY, _values(world, payment_condition_type_id=uuid4()), actor="sub")

    inactive = world.payment.add("CREDIT", status="INACTIVE")
    with pytest.raises(PaymentConditionTypeInactiveError):
        world.service.create(COMPANY, _values(world, payment_condition_type_id=inactive), actor="sub")

    world.payment.unavailable = True
    with pytest.raises(DependencyUnavailableError) as error:
        world.service.create(COMPANY, _values(world), actor="sub")
    assert error.value.provider == "payment-reference"
    assert "add" not in world.repository.events


@pytest.mark.parametrize(("code", "days"), [("CASH", 15), ("CREDIT", 0), ("FINANCING", 0)])
def test_terms_must_match_type_code(world, code, days):
    with pytest.raises(PaymentTermsInconsistentError):
        world.service.create(COMPANY, _values(world, code=code, payment_terms_days=days), actor="sub")


def test_default_mark_clears_previous_in_currency(world):
    world.service.create(COMPANY, _values(world, is_default=True, currency_code="usd"), actor="sub")
    assert world.repository.events[-3:] == ["lock_supplier", "clear_default:USD", "add"]


def test_ds_06_terms_change_reads_code_even_if_type_inactive(world):
    current = world.service.create(COMPANY, _values(world, valid_from=NOW), actor="sub")
    world.payment.deactivate(current.payment_condition_type_id)
    calls = len(world.payment.calls)

    updated = world.service.update(current, _values(world, payment_condition_type_id=current.payment_condition_type_id,
                                                     payment_terms_days=45, valid_from=NOW), version=1, actor="sub")
    assert updated.payment_terms_days == 45
    assert len(world.payment.calls) == calls + 1

    with pytest.raises(PaymentTermsInconsistentError):
        world.service.update(current, _values(world, payment_condition_type_id=current.payment_condition_type_id,
                                              payment_terms_days=0, valid_from=NOW), version=1, actor="sub")


def test_update_without_type_or_terms_change_does_not_call_payment_reference(world):
    current = world.service.create(COMPANY, _values(world, valid_from=NOW), actor="sub")
    calls = len(world.payment.calls)

    world.service.update(current, _values(world, payment_condition_type_id=current.payment_condition_type_id,
                                          credit_limit=None, interest_rate_percentage=None, valid_from=NOW,
                                          cash_discount_percentage=None), version=1, actor="sub")
    assert len(world.payment.calls) == calls


def test_deactivate_clears_default_and_reactivate_checks_supplier_and_type(world):
    current = world.service.create(COMPANY, _values(world, is_default=True), actor="sub")

    world.service.deactivate(current, version=1, actor="sub")
    assert (current.status, current.is_default) == ("INACTIVE", False)

    world.supplier.status = "BLOCKED"
    with pytest.raises(CompanySupplierBlockedError):
        world.service.reactivate(current, version=2, actor="sub")

    world.supplier.status = "ACTIVE"
    world.payment.deactivate(current.payment_condition_type_id)
    with pytest.raises(PaymentConditionTypeInactiveError):
        world.service.reactivate(current, version=2, actor="sub")
