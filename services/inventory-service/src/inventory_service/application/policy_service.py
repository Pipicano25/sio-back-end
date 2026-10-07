"""Políticas de inventario de la empresa y por producto–sucursal (FR-010 a FR-022; DS-01 a DS-03; R-06, R-07).

- Escritura: usuario humano con el permiso (comodín de `administradores` y
  `supervisores`, DS-14) y membresía en la empresa; el usuario operativo de la
  membresía va al evento de auditoría.
- Lectura: permiso de lectura y alcance por empresa (lo resuelve la capa API).
- Solo configuración: `PERIODIC`, `JIT`, `AUTO_DRAFT` y `auto_purchase_enabled` se
  guardan sin cambiar el motor ni generar compras (DS-02, DS-03).
"""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from typing import Any
from uuid import UUID

from sio_audit.event import AuditEvent
from sio_audit.outbox import record_audit_event
from sqlalchemy.orm import Session

from inventory_service.application.adjustment_service import keycloak_uuid
from inventory_service.application.branch_access import OperatorAccess, require_membership
from inventory_service.application.exceptions import NotFoundError, ValidationFailedError, field_error
from inventory_service.application.ports import CompanyAccessDirectory
from inventory_service.application.reference_validation import ReferenceValidator
from inventory_service.domain.quantities import format_decimal
from inventory_service.infrastructure.repository import (
    COMPANY_POLICY_FIELDS,
    PRODUCT_POLICY_FIELDS,
    CompanyPolicyRow,
    Page,
    ProductPolicyRow,
    SqlPolicyRepository,
)

ZERO = Decimal(0)
ONE = Decimal(1)
MIN_WINDOW, MAX_WINDOW = 1, 3650


def level_errors(data: Any) -> list[dict[str, str]]:
    """Rangos de §9.5 (R-07) con su causa en `errors[].code`."""
    errors: list[dict[str, str]] = []
    if data.minimum_stock is None or data.minimum_stock < ZERO:
        errors.append(field_error("minimum_stock", "INVALID_LEVELS", "El stock mínimo debe ser mayor o igual que 0."))
    if data.target_stock is not None:
        if data.target_stock < ZERO:
            errors.append(field_error("target_stock", "INVALID_LEVELS", "El stock objetivo debe ser mayor o igual que 0."))
        elif data.minimum_stock is not None and data.target_stock < data.minimum_stock:
            errors.append(
                field_error("target_stock", "INVALID_LEVELS", "El stock objetivo no puede ser menor que el mínimo.")
            )
    if data.service_level is not None and not ZERO < data.service_level < ONE:
        errors.append(
            field_error("service_level", "INVALID_SERVICE_LEVEL", "El nivel de servicio debe ser mayor que 0 y menor que 1.")
        )
    if not MIN_WINDOW <= data.calculation_window_days <= MAX_WINDOW:
        errors.append(
            field_error(
                "calculation_window_days",
                "INVALID_WINDOW",
                f"La ventana de cálculo debe estar entre {MIN_WINDOW} y {MAX_WINDOW} días.",
            )
        )
    return errors


def _snapshot(row: Any, fields: tuple[str, ...]) -> dict[str, Any] | None:
    if row is None:
        return None
    values: dict[str, Any] = {}
    for name in (*fields, "is_active", "version"):
        value = getattr(row, name)
        values[name] = format_decimal(value) if isinstance(value, Decimal) else value
    return values


class PolicyService:
    def __init__(
        self,
        repository: SqlPolicyRepository,
        validator: ReferenceValidator,
        access: CompanyAccessDirectory,
        *,
        request_id: Callable[[], UUID | None],
    ) -> None:
        self._repository = repository
        self._validator = validator
        self._access = access
        self._request_id = request_id

    def _hook(self, action: str, entity_type: str, fields: tuple[str, ...], operator: OperatorAccess, subject: str):
        def hook(session: Session, previous: Any, row: Any) -> None:
            record_audit_event(
                session,
                AuditEvent(
                    event_id=None,
                    action=action,
                    entity_type=entity_type,
                    entity_id=row.id,
                    result="SUCCESS",
                    occurred_at=row.updated_at,
                    company_id=row.company_id,
                    branch_id=getattr(row, "branch_id", None),
                    application_user_id=operator.application_user_id,
                    keycloak_user_id=keycloak_uuid(subject),
                    request_id=self._request_id(),
                    correlation_id=row.id,
                    previous_values=_snapshot(previous, fields),
                    new_values=_snapshot(row, fields),
                ),
            )

        return hook

    # Empresa (R-06) --------------------------------------------------------------------

    def company_policy(self, company_id: UUID) -> CompanyPolicyRow | None:
        return self._repository.company_policy(company_id)

    def create_company_policy(self, company_id: UUID, data: Any, subject: str) -> CompanyPolicyRow:
        operator = require_membership(self._access, company_id)
        values = {name: getattr(data, name) for name in COMPANY_POLICY_FIELDS}
        hook = self._hook("SET_COMPANY_INVENTORY_POLICY", "CompanyInventoryPolicy", COMPANY_POLICY_FIELDS, operator, subject)
        return self._repository.create_company_policy(company_id, values, subject, hook)

    def update_company_policy(self, company_id: UUID, data: Any, subject: str) -> CompanyPolicyRow:
        operator = require_membership(self._access, company_id)
        values = {name: getattr(data, name) for name in COMPANY_POLICY_FIELDS}
        hook = self._hook("SET_COMPANY_INVENTORY_POLICY", "CompanyInventoryPolicy", COMPANY_POLICY_FIELDS, operator, subject)
        return self._repository.update_company_policy(company_id, data.version, values, subject, hook)

    # Producto (R-07) ---------------------------------------------------------------------

    def product_policy(self, company_id: UUID, policy_id: UUID) -> ProductPolicyRow:
        row = self._repository.product_policy(company_id, policy_id)
        if row is None:
            raise NotFoundError()
        return row

    def list_product_policies(self, company_id: UUID, **filters: Any) -> Page:
        return self._repository.list_product_policies(company_id, **filters)

    def create_product_policy(self, company_id: UUID, data: Any, subject: str) -> ProductPolicyRow:
        operator = require_membership(self._access, company_id)
        errors = level_errors(data)
        self._validator.validate_branch(company_id, data.branch_id, errors)
        errors.extend(self._validator.validate_products(company_id, [("company_product_id", data.company_product_id)]))
        if errors:
            raise ValidationFailedError(errors)
        values = {name: getattr(data, name) for name in PRODUCT_POLICY_FIELDS}
        hook = self._hook("CREATE_INVENTORY_POLICY", "InventoryPolicy", PRODUCT_POLICY_FIELDS, operator, subject)
        return self._repository.create_product_policy(
            company_id, data.branch_id, data.company_product_id, values, subject, hook
        )

    def update_product_policy(self, company_id: UUID, policy_id: UUID, data: Any, subject: str) -> ProductPolicyRow:
        operator = require_membership(self._access, company_id)
        errors = level_errors(data)
        if errors:
            raise ValidationFailedError(errors)
        values = {name: getattr(data, name) for name in PRODUCT_POLICY_FIELDS}
        hook = self._hook("UPDATE_INVENTORY_POLICY", "InventoryPolicy", PRODUCT_POLICY_FIELDS, operator, subject)
        return self._repository.update_product_policy(company_id, policy_id, data.version, values, subject, hook)

    def deactivate_product_policy(self, company_id: UUID, policy_id: UUID, data: Any, subject: str) -> ProductPolicyRow:
        operator = require_membership(self._access, company_id)
        hook = self._hook("DEACTIVATE_INVENTORY_POLICY", "InventoryPolicy", PRODUCT_POLICY_FIELDS, operator, subject)
        return self._repository.deactivate_product_policy(company_id, policy_id, data.version, subject, hook)

