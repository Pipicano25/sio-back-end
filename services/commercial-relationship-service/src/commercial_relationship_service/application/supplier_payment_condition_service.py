"""Casos de uso de condiciones de pago del proveedor (FR-030 a FR-038; R-04, R-08; DS-06).

FR-031 sin cambios: el proveedor debe estar `ACTIVE` al registrar y al
reactivar (`INACTIVE` y `BLOCKED` con causas separadas, I1). El `code` del
tipo de condición se lee de Payment Reference en cada validación y nunca se
guarda (C-10). Las llamadas a Payment Reference se hacen fuera de la
transacción de escritura.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from commercial_relationship_service.application.exceptions import (
    PaymentConditionTypeInactiveError,
    PaymentConditionTypeNotFoundError,
)
from commercial_relationship_service.application.internal_references import (
    require_active_supplier,
)
from commercial_relationship_service.application.mutation import touch, unchanged
from commercial_relationship_service.application.ports import (
    PaymentConditionTypeRef,
    PaymentReferenceDirectory,
)
from commercial_relationship_service.domain.currency import (
    validate_amount_scale,
    validate_currency,
)
from commercial_relationship_service.domain.payment_terms import validate_payment_terms
from commercial_relationship_service.domain.rules import require_active_for_mark
from commercial_relationship_service.domain.status import (
    ACTIVE,
    DEACTIVATE,
    REACTIVATE,
    next_status,
)
from commercial_relationship_service.domain.validity import validate_period

TYPE_FIELD = "payment_condition_type_id"
EDITABLE_FIELDS = (
    TYPE_FIELD,
    "currency_code",
    "payment_terms_days",
    "credit_limit",
    "interest_rate_percentage",
    "cash_discount_percentage",
    "is_default",
    "valid_from",
    "valid_to",
)


def _validate_values(values: dict[str, Any]) -> dict[str, Any]:
    currency = validate_currency(values["currency_code"])

    if values["credit_limit"] is not None:
        validate_amount_scale(values["credit_limit"], currency, field="credit_limit")

    return {**values, "currency_code": currency}


class SupplierPaymentConditionService:
    """Registro, mantenimiento y estados de condiciones de pago."""

    def __init__(self, repository, supplier_repository, payment_factory) -> None:
        self._repository = repository
        self._suppliers = supplier_repository
        # Payment Reference se resuelve solo cuando hace falta (DS-06).
        self._payment_factory = payment_factory

    def create(self, company_id: UUID, values: dict[str, Any], *, actor: str):
        """FR-030 a FR-035: entrada → proveedor → tipo y plazo → persistencia."""
        values = _validate_values(values)
        require_active_supplier(self._suppliers, values["company_supplier_id"], company_id)

        if values["valid_from"] is None:
            values["valid_from"] = self._now()

        validate_period(values["valid_from"], values["valid_to"])
        condition_type = self._active_type(values[TYPE_FIELD])
        validate_payment_terms(condition_type.code, values["payment_terms_days"])

        model = self._repository.build(company_id=company_id, created_by=actor, updated_by=actor, **values)

        if values["is_default"]:
            self._repository.lock_supplier(values["company_supplier_id"])
            self._repository.clear_default(
                values["company_supplier_id"], values["currency_code"], exclude_id=None, actor=actor
            )

        return self._repository.add(model, duplicates=self._repository.duplicates)

    def update(self, current, values: dict[str, Any], *, version: int, actor: str):
        """`PUT` en cualquier estado; Payment Reference solo si cambian el tipo o el plazo (DS-06)."""
        values = _validate_values(values)
        require_active_for_mark(current.status, marked=values["is_default"], field="is_default")

        if values["valid_from"] is None:
            values["valid_from"] = current.valid_from

        validate_period(values["valid_from"], values["valid_to"])

        if values[TYPE_FIELD] != current.payment_condition_type_id:
            condition_type = self._active_type(values[TYPE_FIELD])
            validate_payment_terms(condition_type.code, values["payment_terms_days"])

        elif values["payment_terms_days"] != current.payment_terms_days:
            # Solo cambia el plazo: se lee el código aunque el tipo esté inactivo (DS-06).
            condition_type = self._type(values[TYPE_FIELD])
            validate_payment_terms(condition_type.code, values["payment_terms_days"])

        self._repository.lock_supplier(current.company_supplier_id)
        model = self._repository.load_for_update(current.id, expected_version=version)

        if unchanged(model, values):
            self._repository.release()
            return model

        if values["is_default"] and (
            not model.is_default or values["currency_code"] != model.currency_code
        ):
            self._repository.clear_default(
                model.company_supplier_id, values["currency_code"], exclude_id=model.id, actor=actor
            )

        for name in EDITABLE_FIELDS:
            setattr(model, name, values[name])

        touch(model, actor)
        return self._repository.save(model, duplicates=self._repository.duplicates)

    def deactivate(self, current, *, version: int, actor: str):
        """Inactivar retira `is_default` (DS-05); no consulta Payment Reference."""
        model = self._repository.load_for_update(current.id, expected_version=version)
        model.status = next_status(model.status, DEACTIVATE)
        model.is_default = False
        touch(model, actor)
        return self._repository.save(model, duplicates={})

    def reactivate(self, current, *, version: int, actor: str):
        """FR-031 y FR-032: proveedor `ACTIVE` y tipo de condición `ACTIVE`."""
        next_status(current.status, REACTIVATE)
        require_active_supplier(self._suppliers, current.company_supplier_id, current.company_id)
        self._active_type(current.payment_condition_type_id)

        model = self._repository.load_for_update(current.id, expected_version=version)
        model.status = next_status(model.status, REACTIVATE)
        touch(model, actor)
        return self._repository.save(model, duplicates=self._repository.duplicates)

    # -------------------------------------------------------------- internos

    def _type(self, condition_type_id: UUID) -> PaymentConditionTypeRef:
        directory: PaymentReferenceDirectory = self._payment_factory()
        condition_type = directory.get_condition_type(condition_type_id)

        if condition_type is None:
            raise PaymentConditionTypeNotFoundError(field=TYPE_FIELD)

        return condition_type

    def _active_type(self, condition_type_id: UUID) -> PaymentConditionTypeRef:
        condition_type = self._type(condition_type_id)

        if condition_type.status != ACTIVE:
            raise PaymentConditionTypeInactiveError(field=TYPE_FIELD)

        return condition_type

    def _now(self):
        now = self._repository.database_now()
        self._repository.release()
        return now
