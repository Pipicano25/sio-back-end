"""Validación de referencias contra sus dueños (FR-013, FR-034; research.md R-07).

Se ejecuta **antes** de abrir la transacción (no se retienen bloqueos durante
llamadas HTTP). Reúne todas las referencias inválidas en un solo `422`; una
dependencia no disponible se propaga como `503` sin aplicar nada.

- Operaciones nuevas: sucursal (incluye la empresa) `ACTIVE`, usuario operativo de
  la empresa `ACTIVE` y productos de la empresa `ACTIVE` con
  `inventory_control_enabled` (una sola consulta por lote).
- Reversos: solo el usuario operativo, que debe existir y ser de la empresa aunque
  esté `INACTIVE`; sucursal y producto no se vuelven a validar.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from inventory_service.application.exceptions import ValidationFailedError, field_error
from inventory_service.application.ports import CompanyProductDirectory, OperationalContextDirectory

ACTIVE = "ACTIVE"


@dataclass(frozen=True, slots=True)
class ValidatedReferences:
    """Datos de las referencias que solo viajan al evento de auditoría (no se guardan)."""

    keycloak_user_id: UUID | None
    currency_code: str | None = None
    """`default_currency` de la empresa, solo si la operación crea capas (013 R-03b)."""


class ReferenceValidator:
    def __init__(self, operational_context: OperationalContextDirectory, products: CompanyProductDirectory) -> None:
        self._oc = operational_context
        self._products = products

    def validate_operation(
        self,
        company_id: UUID,
        branch_id: UUID,
        application_user_id: UUID,
        line_products: Sequence[UUID],
        *,
        needs_currency: bool = False,
    ) -> ValidatedReferences:
        errors: list[dict[str, str]] = []

        branch = self._oc.get_branch(branch_id)
        if branch is None:
            errors.append(field_error("branch_id", "BRANCH_NOT_FOUND", "La sucursal no existe."))
        elif branch.company_id != company_id:
            errors.append(field_error("branch_id", "BRANCH_NOT_IN_COMPANY", "La sucursal no pertenece a la empresa."))
        elif branch.company_status != ACTIVE:
            errors.append(field_error("company_id", "COMPANY_INACTIVE", "La empresa no está activa."))
        elif branch.status != ACTIVE:
            errors.append(field_error("branch_id", "BRANCH_INACTIVE", "La sucursal no está activa."))

        keycloak_user_id, user_errors = self._check_user(company_id, application_user_id, require_active=True)
        errors.extend(user_errors)

        found = self._products.lookup(dict.fromkeys(line_products))
        for index, product_id in enumerate(line_products):
            field = f"lines[{index}].company_product_id"
            product = found.get(product_id)
            if product is None or product.company_id != company_id:
                errors.append(field_error(field, "COMPANY_PRODUCT_NOT_FOUND", "El producto empresarial no existe en la empresa."))
            elif product.status != ACTIVE:
                errors.append(field_error(field, "COMPANY_PRODUCT_INACTIVE", "El producto empresarial no está activo."))
            elif not product.inventory_control_enabled:
                errors.append(
                    field_error(field, "INVENTORY_CONTROL_DISABLED", "El producto no tiene control de inventario.")
                )

        currency_code = self.company_currency(company_id, errors) if needs_currency else None

        if errors:
            raise ValidationFailedError(errors)

        return ValidatedReferences(keycloak_user_id=keycloak_user_id, currency_code=currency_code)

    def company_currency(self, company_id: UUID, errors: list[dict[str, str]]) -> str | None:
        """Moneda de valoración (013 R-03b): `companies/{id}` con la identidad técnica, fuera de la transacción."""
        currency = self._oc.get_company_currency(company_id)
        if currency is None:
            errors.append(field_error("company_id", "COMPANY_NOT_FOUND", "La empresa no existe."))
        return currency

    def validate_products(self, company_id: UUID, products: Sequence[tuple[str, UUID]]) -> list[dict[str, str]]:
        """Productos aptos para movimientos de inventario (013: ajustes, conteos y políticas); errores por campo."""
        errors: list[dict[str, str]] = []
        found = self._products.lookup(dict.fromkeys(product for _, product in products))
        for field, product_id in products:
            product = found.get(product_id)
            if product is None or product.company_id != company_id:
                errors.append(field_error(field, "COMPANY_PRODUCT_NOT_FOUND", "El producto empresarial no existe en la empresa."))
            elif product.status != ACTIVE:
                errors.append(field_error(field, "COMPANY_PRODUCT_INACTIVE", "El producto empresarial no está activo."))
            elif not product.inventory_control_enabled:
                errors.append(
                    field_error(field, "INVENTORY_CONTROL_DISABLED", "El producto no tiene control de inventario.")
                )
        return errors

    def validate_branch(self, company_id: UUID, branch_id: UUID, errors: list[dict[str, str]]) -> None:
        """Sucursal de la empresa y `ACTIVE` (políticas de producto, R-07)."""
        branch = self._oc.get_branch(branch_id)
        if branch is None:
            errors.append(field_error("branch_id", "BRANCH_NOT_FOUND", "La sucursal no existe."))
        elif branch.company_id != company_id:
            errors.append(field_error("branch_id", "BRANCH_NOT_IN_COMPANY", "La sucursal no pertenece a la empresa."))
        elif branch.company_status != ACTIVE:
            errors.append(field_error("company_id", "COMPANY_INACTIVE", "La empresa no está activa."))
        elif branch.status != ACTIVE:
            errors.append(field_error("branch_id", "BRANCH_INACTIVE", "La sucursal no está activa."))

    def validate_reversal_user(self, company_id: UUID, application_user_id: UUID) -> UUID | None:
        keycloak_user_id, errors = self._check_user(company_id, application_user_id, require_active=False)
        if errors:
            raise ValidationFailedError(errors)
        return keycloak_user_id

    def _check_user(
        self, company_id: UUID, application_user_id: UUID, *, require_active: bool
    ) -> tuple[UUID | None, list[dict[str, str]]]:
        user = self._oc.get_application_user(application_user_id)

        if user is None or user.company_id != company_id:
            return None, [
                field_error("application_user_id", "APPLICATION_USER_NOT_FOUND", "El usuario operativo no existe en la empresa.")
            ]

        if require_active and user.status != ACTIVE:
            return None, [
                field_error("application_user_id", "APPLICATION_USER_INACTIVE", "El usuario operativo no está activo.")
            ]

        return user.keycloak_user_id, []
