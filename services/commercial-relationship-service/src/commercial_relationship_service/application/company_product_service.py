"""Casos de uso de productos empresariales (FR-010 a FR-018, FR-062; R-04, R-12, R-14).

El alcance por empresa (membresía y empresa activa) lo resuelve la capa API
antes de llegar aquí (R-03). Las llamadas a Product Catalog se hacen fuera de
cualquier transacción de escritura; la inserción es una transacción corta.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from commercial_relationship_service.application import audit_events
from commercial_relationship_service.application.company_scope import (
    CompanyScopeService,
    RequestIdentity,
)
from commercial_relationship_service.application.exceptions import (
    BatchLimitExceededError,
    DuplicateAdoptionError,
    DuplicateInternalCodeError,
    GlobalProductInactiveError,
    GlobalProductNotEligibleError,
    GlobalProductNotFoundError,
)
from commercial_relationship_service.application.ports import ProductCatalogDirectory
from commercial_relationship_service.domain.currency import validate_currency
from commercial_relationship_service.domain.rules import code_key, validate_inventory_flags
from commercial_relationship_service.domain.status import DEACTIVATE, REACTIVATE, next_status

BATCH_LIMIT = 100

EDITABLE_FIELDS = (
    "internal_code",
    "reference_code",
    "display_name",
    "short_name",
    "currency_code",
    "inventory_control_enabled",
    "lot_tracking_enabled",
    "expiration_tracking_enabled",
    "is_purchasable",
    "is_sellable",
)


@dataclass(frozen=True, slots=True)
class BatchItem:
    """Elemento de la consulta por lotes: `model` es `None` si no se encontró."""

    id: UUID
    model: Any | None


def _validate_values(values: dict[str, Any]) -> dict[str, Any]:
    """Moneda de la lista cerrada y banderas (FR-014, RN-03). Sin precio ni costo (spec 019)."""
    currency = validate_currency(values["currency_code"])
    validate_inventory_flags(
        inventory_control_enabled=values["inventory_control_enabled"],
        lot_tracking_enabled=values["lot_tracking_enabled"],
        expiration_tracking_enabled=values["expiration_tracking_enabled"],
    )
    return {**values, "currency_code": currency}


def _require_active_product(catalog: ProductCatalogDirectory, global_product_id: UUID, *, eligible: bool) -> None:
    ref = catalog.lookup_product(global_product_id)

    if not ref.found:
        raise GlobalProductNotFoundError(field="global_product_id")

    if ref.status != "ACTIVE":
        raise GlobalProductInactiveError(field="global_product_id")

    if eligible and not ref.eligible_for_adoption:
        raise GlobalProductNotEligibleError(field="global_product_id")


class CompanyProductService:
    """Adopción, mantenimiento, estados y consulta por lotes."""

    def __init__(self, repository, catalog_factory) -> None:
        self._repository = repository
        # La fábrica se resuelve solo cuando hace falta Product Catalog: así las
        # operaciones que no lo usan nunca obtienen el token técnico.
        self._catalog_factory = catalog_factory

    # ---------------------------------------------------------------- adopción

    def adopt(self, company_id: UUID, values: dict[str, Any], *, actor: str):
        """FR-011: validaciones → unicidad local → elegibilidad → primer uso → inserción."""
        values = _validate_values(values)
        global_product_id = values["global_product_id"]

        if self._repository.adoption_exists(company_id, global_product_id):
            raise DuplicateAdoptionError(field="global_product_id")

        if self._repository.code_taken(company_id, values["internal_code"]):
            raise DuplicateInternalCodeError(field="internal_code")

        catalog: ProductCatalogDirectory = self._catalog_factory()
        _require_active_product(catalog, global_product_id, eligible=True)
        # Primer uso síncrono antes de confirmar (DS-01): si falla, no se guarda nada.
        catalog.register_first_use(global_product_id)

        return self._repository.create(
            audit=audit_events.spec(audit_events.ADOPT_COMPANY_PRODUCT, "CompanyProduct", company_id),
            company_id=company_id,
            created_by=actor,
            updated_by=actor,
            **values,
        )

    # ----------------------------------------------------------- mantenimiento

    def update(self, current, values: dict[str, Any], *, version: int, actor: str):
        """`PUT` en cualquier estado (DS-17): no consulta Product Catalog ni cambia el estado."""
        values = _validate_values(values)

        if code_key(values["internal_code"]) != code_key(current.internal_code) and (
            self._repository.code_taken(current.company_id, values["internal_code"], exclude_id=current.id)
        ):
            raise DuplicateInternalCodeError(field="internal_code")

        model = self._repository.load_for_update(current.id, expected_version=version)

        if all(_same(getattr(model, name), values[name]) for name in EDITABLE_FIELDS):
            self._repository.release()
            return model

        for name in EDITABLE_FIELDS:
            setattr(model, name, values[name])

        _touch(model, actor)
        return self._repository.save(model, duplicates=self._repository.duplicates, audit=audit_events.spec(audit_events.UPDATE_COMPANY_PRODUCT, "CompanyProduct", model.company_id))

    def deactivate(self, current, *, version: int, actor: str):
        """Inactivar no consulta Product Catalog; se permite con la empresa inactiva."""
        model = self._repository.load_for_update(current.id, expected_version=version)
        model.status = next_status(model.status, DEACTIVATE)
        _touch(model, actor)
        return self._repository.save(model, duplicates={}, audit=audit_events.spec(audit_events.DEACTIVATE_COMPANY_PRODUCT, "CompanyProduct", model.company_id))

    def reactivate(self, current, *, version: int, actor: str):
        """Exige el producto global `ACTIVE`; no exige completitud ni registra primer uso (FR-016)."""
        next_status(current.status, REACTIVATE)
        _require_active_product(self._catalog_factory(), current.global_product_id, eligible=False)

        model = self._repository.load_for_update(current.id, expected_version=version)
        model.status = next_status(model.status, REACTIVATE)
        _touch(model, actor)
        return self._repository.save(model, duplicates={}, audit=audit_events.spec(audit_events.REACTIVATE_COMPANY_PRODUCT, "CompanyProduct", model.company_id))

    # ------------------------------------------------------------------ lotes

    def batch_lookup(
        self,
        ids: list[UUID],
        *,
        identity: RequestIdentity,
        scope: CompanyScopeService,
    ) -> list[BatchItem]:
        """FR-062 / R-12: 1–100 UUID; duplicados ignorados; orden de entrada.

        Sin exención técnica, una consulta de acceso por empresa distinta entre los
        encontrados; los de empresas sin membresía se informan como no encontrados.
        """
        unique = list(dict.fromkeys(ids))

        if len(unique) > BATCH_LIMIT:
            raise BatchLimitExceededError(field="ids")

        rows = {row.id: row for row in self._repository.get_many(unique)}

        if not identity.technical_lookup:
            visible = {company_id: scope.is_member(company_id) for company_id in {row.company_id for row in rows.values()}}
            rows = {row_id: row for row_id, row in rows.items() if visible[row.company_id]}

        return [BatchItem(id=item_id, model=rows.get(item_id)) for item_id in unique]


def _same(current: Any, new: Any) -> bool:
    if isinstance(current, Decimal) or isinstance(new, Decimal):
        return Decimal(current) == Decimal(new)
    return current == new


def _touch(model, actor: str) -> None:
    model.updated_by = actor
    model.updated_at = datetime.now(UTC)
