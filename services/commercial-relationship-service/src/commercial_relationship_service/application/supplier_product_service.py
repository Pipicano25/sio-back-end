"""Casos de uso de productos de proveedor (FR-020 a FR-028; R-04, R-07, R-09; H-02).

FR-021 sin cambios: el proveedor debe estar `ACTIVE` al registrar y al
reactivar; `INACTIVE` y `BLOCKED` se rechazan con causas separadas (I1). La
unidad de compra es siempre la unidad base del producto global (DS-07, OP-01).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from commercial_relationship_service.application import audit_events
from commercial_relationship_service.application.exceptions import (
    DuplicateSupplierProductError,
    PresentationInactiveError,
    PurchaseUnitNotBaseUnitError,
)
from commercial_relationship_service.application.internal_references import (
    PRESENTATION_FIELD,
    require_active_supplier,
    require_presentation,
    require_product,
)
from commercial_relationship_service.application.mutation import touch, unchanged
from commercial_relationship_service.application.ports import ProductCatalogDirectory
from commercial_relationship_service.domain.currency import validate_currency
from commercial_relationship_service.domain.rules import require_active_for_mark
from commercial_relationship_service.domain.status import (
    ACTIVE,
    DEACTIVATE,
    REACTIVATE,
    next_status,
)

EDITABLE_FIELDS = (
    PRESENTATION_FIELD,
    "supplier_product_code",
    "purchase_unit_id",
    "minimum_order_quantity",
    "pack_quantity",
    "negotiated_unit_cost",
    "currency_code",
    "expected_supplier_lead_time_hours",
    "priority",
    "is_preferred",
)


class SupplierProductService:
    """Registro, mantenimiento y estados de productos de proveedor."""

    def __init__(
        self,
        repository,
        product_repository,
        supplier_repository,
        presentation_repository,
        catalog_factory,
    ) -> None:
        self._repository = repository
        self._products = product_repository
        self._suppliers = supplier_repository
        self._presentations = presentation_repository
        self._catalog_factory = catalog_factory

    # ---------------------------------------------------------------- registro

    def create(self, company_id: UUID, values: dict[str, Any], *, actor: str):
        """R-09: entrada → referencias internas → unicidad → unidad base → persistencia."""
        values = {**values, "currency_code": validate_currency(values["currency_code"])}
        require_active_supplier(self._suppliers, values["company_supplier_id"], company_id)
        product = require_product(self._products, values["company_product_id"], company_id)
        self._check_presentation(company_id, product.id, values[PRESENTATION_FIELD])

        if self._repository.active_relation_exists(
            company_supplier_id=values["company_supplier_id"],
            company_product_id=product.id,
            company_product_presentation_id=values[PRESENTATION_FIELD],
        ):
            raise DuplicateSupplierProductError

        self._check_base_unit(product.global_product_id, values["purchase_unit_id"])

        model = self._repository.build(company_id=company_id, created_by=actor, updated_by=actor, **values)

        if values["is_preferred"]:
            self._repository.lock_product(product.id)
            self._repository.clear_preferred(product.id, exclude_id=None, actor=actor)

        return self._repository.add(model, duplicates=self._repository.duplicates, audit=audit_events.spec(audit_events.CREATE_SUPPLIER_PRODUCT, "SupplierProduct", model.company_id))

    # ----------------------------------------------------------- mantenimiento

    def update(self, current, values: dict[str, Any], *, version: int, actor: str):
        """`PUT` en cualquier estado; H-02: solo se revalidan la presentación y la unidad nuevas."""
        values = {**values, "currency_code": validate_currency(values["currency_code"])}
        require_active_for_mark(current.status, marked=values["is_preferred"], field="is_preferred")
        presentation_changed = values[PRESENTATION_FIELD] != current.company_product_presentation_id

        if presentation_changed:
            self._check_presentation(current.company_id, current.company_product_id, values[PRESENTATION_FIELD])

            if current.status == ACTIVE and self._repository.active_relation_exists(
                company_supplier_id=current.company_supplier_id,
                company_product_id=current.company_product_id,
                company_product_presentation_id=values[PRESENTATION_FIELD],
                exclude_id=current.id,
            ):
                raise DuplicateSupplierProductError

        if values["purchase_unit_id"] != current.purchase_unit_id:
            product = require_product(
                self._products, current.company_product_id, current.company_id, active=False
            )
            self._check_base_unit(product.global_product_id, values["purchase_unit_id"])

        self._repository.lock_product(current.company_product_id)
        model = self._repository.load_for_update(current.id, expected_version=version)

        if unchanged(model, values):
            self._repository.release()
            return model

        if values["is_preferred"] and not model.is_preferred:
            self._repository.clear_preferred(model.company_product_id, exclude_id=model.id, actor=actor)

        for name in EDITABLE_FIELDS:
            setattr(model, name, values[name])

        touch(model, actor)
        return self._repository.save(model, duplicates=self._repository.duplicates, audit=audit_events.spec(audit_events.UPDATE_SUPPLIER_PRODUCT, "SupplierProduct", model.company_id))

    def deactivate(self, current, *, version: int, actor: str):
        """Inactivar retira `is_preferred` (DS-05)."""
        model = self._repository.load_for_update(current.id, expected_version=version)
        model.status = next_status(model.status, DEACTIVATE)
        model.is_preferred = False
        touch(model, actor)
        return self._repository.save(model, duplicates={}, audit=audit_events.spec(audit_events.DEACTIVATE_SUPPLIER_PRODUCT, "SupplierProduct", model.company_id))

    def reactivate(self, current, *, version: int, actor: str):
        """FR-027: proveedor, producto y presentación `ACTIVE` y relación única entre `ACTIVE`."""
        next_status(current.status, REACTIVATE)
        require_active_supplier(self._suppliers, current.company_supplier_id, current.company_id)
        require_product(self._products, current.company_product_id, current.company_id)

        if current.company_product_presentation_id is not None:
            presentation = self._presentations.get(current.company_product_presentation_id)

            if presentation is None or presentation.status != ACTIVE:
                raise PresentationInactiveError(field=PRESENTATION_FIELD)

        if self._repository.active_relation_exists(
            company_supplier_id=current.company_supplier_id,
            company_product_id=current.company_product_id,
            company_product_presentation_id=current.company_product_presentation_id,
            exclude_id=current.id,
        ):
            raise DuplicateSupplierProductError

        model = self._repository.load_for_update(current.id, expected_version=version)
        model.status = next_status(model.status, REACTIVATE)
        touch(model, actor)
        return self._repository.save(model, duplicates=self._repository.duplicates, audit=audit_events.spec(audit_events.REACTIVATE_SUPPLIER_PRODUCT, "SupplierProduct", model.company_id))

    # -------------------------------------------------------------- internos

    def _check_presentation(self, company_id: UUID, company_product_id: UUID, presentation_id: UUID | None) -> None:
        if presentation_id is not None:
            require_presentation(
                self._presentations,
                presentation_id,
                company_id=company_id,
                company_product_id=company_product_id,
                purchasable=True,
            )

    def _check_base_unit(self, global_product_id: UUID, purchase_unit_id: UUID) -> None:
        catalog: ProductCatalogDirectory = self._catalog_factory()
        base_unit = catalog.get_product_base_unit(global_product_id)

        if base_unit is None or base_unit != purchase_unit_id:
            raise PurchaseUnitNotBaseUnitError(field="purchase_unit_id")
