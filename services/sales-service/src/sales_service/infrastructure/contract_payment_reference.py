"""Payment Reference leído de su vista de contrato (spec 025, T044; D27).

Mismo puerto que `HTTPPaymentReferenceDirectory`: `v1_payment_methods` reemplaza a
`GET /global-payment-methods/{id}`. Sin fila → `None` (el `404` de hoy).
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import Engine

from sales_service.application.exceptions import PAYMENT_REFERENCE
from sales_service.application.ports import PaymentMethodInfo
from sales_service.infrastructure.contract_support import ContractReader

_METHOD = "SELECT code, name, status FROM contract.v1_payment_methods WHERE id = :id"


class ContractPaymentReferenceDirectory:
    def __init__(self, *, engine: Engine) -> None:
        self._reader = ContractReader(engine, PAYMENT_REFERENCE)

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
