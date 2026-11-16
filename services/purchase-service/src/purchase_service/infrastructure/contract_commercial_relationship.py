"""Commercial Relationship leído de sus vistas de contrato (spec 025, T052; D27).

Mismo puerto que `HTTPCommercialDirectory`:

- `get_supplier`, `get_payment_condition` y `get_supplier_product` leen `v1_company_suppliers`,
  `v1_supplier_payment_conditions` y `v1_supplier_products` por id (sin fila → `None`, el `404` de hoy).
- `lookup_products` y `lookup_presentations` leen `v1_company_products` y `v1_company_product_presentations` en lotes
  de 100 (`found=false` → ausente). Igual que el batch-lookup técnico, no filtran por empresa: la aplicación compara
  `company_id`.
- `lookup_pricing_coverage` reproduce `POST /companies/{c}/pricing-policies/coverage`: `found` es que la presentación
  existe en la empresa y `covered` que hay al menos una fila de `v1_pricing_coverage` vigente ahora en la moneda pedida.
  Toda presentación pedida recibe respuesta.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import Engine

from purchase_service.application.exceptions import COMMERCIAL_RELATIONSHIP
from purchase_service.application.ports import (
    CompanyPresentationInfo,
    CompanyProductInfo,
    PaymentConditionInfo,
    SupplierInfo,
    SupplierProductInfo,
)
from purchase_service.infrastructure.contract_support import BATCH_LIMIT, ContractReader, distinct_ids

_SUPPLIER = "SELECT company_id, organization_identity_id, display_name, status FROM contract.v1_company_suppliers WHERE id = :id"
_CONDITION = (
    "SELECT company_id, company_supplier_id, payment_condition_type_id, currency_code, payment_terms_days, valid_from,"
    " valid_to, status FROM contract.v1_supplier_payment_conditions WHERE id = :id"
)
_SUPPLIER_PRODUCT = (
    "SELECT company_id, company_supplier_id, company_product_id, company_product_presentation_id,"
    " expected_supplier_lead_time_hours, status FROM contract.v1_supplier_products WHERE id = :id"
)
_PRODUCTS = (
    "SELECT id, company_id, global_product_id, internal_code, display_name, is_purchasable, inventory_control_enabled,"
    " status, purchase_tax_percentage FROM contract.v1_company_products WHERE id = ANY(:ids)"
)
_PRESENTATIONS = (
    "SELECT id, company_id, company_product_id, global_product_presentation_id, is_purchasable, status"
    " FROM contract.v1_company_product_presentations WHERE id = ANY(:ids)"
)
_COVERAGE = (
    "SELECT p.id,"
    " EXISTS (SELECT 1 FROM contract.v1_pricing_coverage c WHERE c.company_id = p.company_id"
    " AND c.company_product_presentation_id = p.id AND c.currency_code = :currency) AS covered"
    " FROM contract.v1_company_product_presentations p WHERE p.company_id = :company_id AND p.id = ANY(:ids)"
)


def _day(value: date | datetime | None) -> date | None:
    """Igual que `date_field`: el API serializa el instante (base en UTC) y Purchase toma sus 10 primeros caracteres."""
    if isinstance(value, datetime):
        return value.astimezone(UTC).date()
    return value


class ContractCommercialDirectory:
    def __init__(self, *, engine: Engine) -> None:
        self._reader = ContractReader(engine, COMMERCIAL_RELATIONSHIP)

    def get_supplier(self, supplier_id: UUID) -> SupplierInfo | None:
        operation = "company_supplier"
        row = self._reader.one(operation, _SUPPLIER, {"id": supplier_id})
        if row is None:
            return None
        required = self._reader.required
        return SupplierInfo(
            id=supplier_id,
            company_id=required(operation, row, "company_id"),
            organization_identity_id=required(operation, row, "organization_identity_id"),
            display_name=required(operation, row, "display_name"),
            status=required(operation, row, "status"),
        )

    def get_payment_condition(self, condition_id: UUID) -> PaymentConditionInfo | None:
        operation = "supplier_payment_condition"
        row = self._reader.one(operation, _CONDITION, {"id": condition_id})
        if row is None:
            return None
        required = self._reader.required
        return PaymentConditionInfo(
            id=condition_id,
            company_id=required(operation, row, "company_id"),
            company_supplier_id=required(operation, row, "company_supplier_id"),
            payment_condition_type_id=required(operation, row, "payment_condition_type_id"),
            currency_code=required(operation, row, "currency_code"),
            payment_terms_days=required(operation, row, "payment_terms_days"),
            valid_from=_day(row.get("valid_from")),
            valid_to=_day(row.get("valid_to")),
            status=required(operation, row, "status"),
        )

    def get_supplier_product(self, supplier_product_id: UUID) -> SupplierProductInfo | None:
        operation = "supplier_product"
        row = self._reader.one(operation, _SUPPLIER_PRODUCT, {"id": supplier_product_id})
        if row is None:
            return None
        required = self._reader.required
        return SupplierProductInfo(
            id=supplier_product_id,
            company_id=required(operation, row, "company_id"),
            company_supplier_id=required(operation, row, "company_supplier_id"),
            company_product_id=required(operation, row, "company_product_id"),
            company_product_presentation_id=row.get("company_product_presentation_id"),
            expected_supplier_lead_time_hours=row.get("expected_supplier_lead_time_hours"),
            status=required(operation, row, "status"),
        )

    def _batch(self, operation: str, sql: str, ids: Sequence[UUID]) -> list[dict]:
        found: list[dict] = []
        distinct = distinct_ids(ids)
        for start in range(0, len(distinct), BATCH_LIMIT):
            found.extend(self._reader.rows(operation, sql, {"ids": distinct[start : start + BATCH_LIMIT]}))
        return found

    def lookup_products(self, ids: Sequence[UUID]) -> dict[UUID, CompanyProductInfo]:
        operation = "company_products_batch"
        required = self._reader.required
        return {
            row["id"]: CompanyProductInfo(
                id=row["id"],
                company_id=required(operation, row, "company_id"),
                global_product_id=required(operation, row, "global_product_id"),
                internal_code=required(operation, row, "internal_code"),
                display_name=required(operation, row, "display_name"),
                is_purchasable=required(operation, row, "is_purchasable"),
                inventory_control_enabled=required(operation, row, "inventory_control_enabled"),
                status=required(operation, row, "status"),
                purchase_tax_percentage=row.get("purchase_tax_percentage"),
            )
            for row in self._batch(operation, _PRODUCTS, ids)
        }

    def lookup_presentations(self, ids: Sequence[UUID]) -> dict[UUID, CompanyPresentationInfo]:
        operation = "company_product_presentations_batch"
        required = self._reader.required
        return {
            row["id"]: CompanyPresentationInfo(
                id=row["id"],
                company_id=required(operation, row, "company_id"),
                company_product_id=required(operation, row, "company_product_id"),
                global_product_presentation_id=required(operation, row, "global_product_presentation_id"),
                is_purchasable=required(operation, row, "is_purchasable"),
                status=required(operation, row, "status"),
            )
            for row in self._batch(operation, _PRESENTATIONS, ids)
        }

    def lookup_pricing_coverage(self, company_id: UUID, currency_code: str, ids: Sequence[UUID]) -> dict[UUID, bool]:
        operation = "pricing_policy_coverage"
        distinct = distinct_ids(ids)
        result: dict[UUID, bool] = {}
        for start in range(0, len(distinct), BATCH_LIMIT):
            chunk = distinct[start : start + BATCH_LIMIT]
            rows = self._reader.rows(
                operation, _COVERAGE, {"company_id": company_id, "currency": currency_code, "ids": chunk}
            )
            covered = {row["id"]: bool(row["covered"]) for row in rows}
            for presentation_id in chunk:  # sin fila = no existe en la empresa (`found=false`)
                result[presentation_id] = covered.get(presentation_id, False)
        return result
