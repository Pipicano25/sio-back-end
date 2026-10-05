"""Filtros del listado de condiciones de pago (FR-038).

Sin `status` solo se devuelven registros `ACTIVE`; `status=ALL` devuelve todos (FR-004).
"""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from fastapi import Query
from pydantic import AwareDatetime

StatusFilter = Literal["ACTIVE", "INACTIVE", "ALL"]


class SupplierPaymentConditionFilters:
    """Estado, proveedor, tipo, moneda, predeterminada y aplicables en un instante (FR-038)."""

    def __init__(
        self,
        status: StatusFilter | None = Query(default=None),
        company_supplier_id: UUID | None = Query(default=None),
        payment_condition_type_id: UUID | None = Query(default=None),
        currency_code: str | None = Query(default=None, min_length=3, max_length=3),
        is_default: bool | None = Query(default=None),
        applicable_at: AwareDatetime | None = Query(default=None),
    ) -> None:
        self.search = None
        self.status = status
        self.applicable_at = applicable_at
        self.columns: dict[str, Any] = {
            "company_supplier_id": company_supplier_id,
            "payment_condition_type_id": payment_condition_type_id,
            "currency_code": None if currency_code is None else currency_code.upper(),
            "is_default": is_default,
        }
