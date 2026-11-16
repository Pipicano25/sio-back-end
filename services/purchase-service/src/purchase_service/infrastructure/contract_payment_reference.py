"""Payment Reference leído de sus vistas de contrato (spec 025, T053; D27).

Mismo puerto que `HTTPPaymentReferenceDirectory`: `v1_payment_condition_types` y `v1_payment_methods` reemplazan a
`GET /global-payment-condition-types/{id}` y `GET /global-payment-methods/{id}`. Sin fila → `None` (el `404`).
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import Engine

from purchase_service.application.exceptions import PAYMENT_REFERENCE
from purchase_service.application.ports import PaymentConditionTypeInfo, PaymentMethodInfo
from purchase_service.infrastructure.contract_support import ContractReader

_TYPE = "SELECT code, status FROM contract.v1_payment_condition_types WHERE id = :id"
_METHOD = "SELECT code, name, status FROM contract.v1_payment_methods WHERE id = :id"


class ContractPaymentReferenceDirectory:
    def __init__(self, *, engine: Engine) -> None:
        self._reader = ContractReader(engine, PAYMENT_REFERENCE)

    def get_condition_type(self, type_id: UUID) -> PaymentConditionTypeInfo | None:
        operation = "payment_condition_type"
        row = self._reader.one(operation, _TYPE, {"id": type_id})
        if row is None:
            return None
        required = self._reader.required
        return PaymentConditionTypeInfo(
            id=type_id, code=required(operation, row, "code"), status=required(operation, row, "status")
        )

    def get_payment_method(self, method_id: UUID) -> PaymentMethodInfo | None:
        operation = "payment_method"
        row = self._reader.one(operation, _METHOD, {"id": method_id})
        if row is None:
            return None
        required = self._reader.required
        return PaymentMethodInfo(
            id=method_id,
            code=required(operation, row, "code"),
            name=required(operation, row, "name"),
            status=required(operation, row, "status"),
        )
