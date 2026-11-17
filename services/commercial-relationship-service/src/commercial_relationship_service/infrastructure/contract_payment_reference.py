"""Payment Reference leído de su vista de contrato (spec 025, T070; D27).

`ContractPaymentReferenceDirectory` implementa `PaymentReferenceDirectory` igual que `HTTPPaymentReferenceDirectory`,
que hoy va con la identidad técnica propia (sin permiso del usuario):

| Método | Vista | Reemplaza |
|---|---|---|
| `get_condition_type` | `v1_payment_condition_types` | `GET /global-payment-condition-types/{id}` |

- Sin fila → `None`, igual que el `404` de hoy. El GET no filtra por estado; la vista tampoco.
- `code` vacío o `status` fuera de `ACTIVE`/`INACTIVE` → la misma indisponibilidad que hoy produce un cuerpo
  inesperado.
- Cualquier error de base → `DependencyUnavailableError("payment-reference")`, el mismo `503` de hoy, con causa
  `contract:<causa>`.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import Engine

from commercial_relationship_service.application.exceptions import PAYMENT_REFERENCE
from commercial_relationship_service.application.ports import PaymentConditionTypeRef
from commercial_relationship_service.infrastructure.contract_support import ContractReader

_TYPE = "SELECT code, status FROM contract.v1_payment_condition_types WHERE id = :id"


class ContractPaymentReferenceDirectory:
    """Tipo de condición de pago por UUID desde la vista de Payment Reference."""

    def __init__(self, *, engine: Engine) -> None:
        self._reader = ContractReader(engine, PAYMENT_REFERENCE)

    def get_condition_type(self, condition_type_id: UUID) -> PaymentConditionTypeRef | None:
        operation = "global_payment_condition_types_get"
        row = self._reader.one(operation, _TYPE, {"id": condition_type_id})
        if row is None:
            return None
        code = row.get("code")
        status = row.get("status")
        if not isinstance(code, str) or not code or status not in {"ACTIVE", "INACTIVE"}:
            raise self._reader.unavailable(operation, "cuerpo_inesperado")
        return PaymentConditionTypeRef(id=condition_type_id, code=code, status=status)
