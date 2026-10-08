"""Casos de uso de presentaciones empresariales (FR-010 a FR-017, FR-081; R-04, R-07, R-09).

El alcance por empresa lo resuelve la capa API (R-03 de la 007). Las llamadas a
Product Catalog se hacen fuera de la transacción de escritura; la persistencia
bloquea el producto empresarial (ámbito de las predeterminadas) y retira la
marca anterior en la misma transacción (DS-04, aclaración 4).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from commercial_relationship_service.application import audit_events
from commercial_relationship_service.application.company_product_service import (
    BATCH_LIMIT,
    BatchItem,
)
from commercial_relationship_service.application.company_scope import (
    CompanyScopeService,
    RequestIdentity,
)
from commercial_relationship_service.application.exceptions import (
    BatchLimitExceededError,
    CompanyProductInactiveError,
    DuplicateInternalCodeError,
    DuplicatePresentationAdoptionError,
    DuplicateSkuError,
    GlobalPresentationInactiveError,
    GlobalPresentationNotEligibleError,
    GlobalPresentationNotFoundError,
    GlobalPresentationOfOtherProductError,
)
from commercial_relationship_service.application.internal_references import require_product
from commercial_relationship_service.application.mutation import touch, unchanged
from commercial_relationship_service.application.ports import ProductCatalogDirectory
from commercial_relationship_service.domain.rules import (
    require_active_for_mark,
    validate_presentation_flags,
)
from commercial_relationship_service.domain.status import (
    ACTIVE,
    DEACTIVATE,
    REACTIVATE,
    next_status,
)

GLOBAL_FIELD = "global_product_presentation_id"
MARKS = ("is_default_purchase", "is_default_sale")
EDITABLE_FIELDS = (
    "internal_code",
    "sku",
    "reference_code",
    "is_purchasable",
    "is_sellable",
    "is_default_purchase",
    "is_default_sale",
)


def _require_global_presentation(
    catalog: ProductCatalogDirectory,
    presentation_id: UUID,
    *,
    global_product_id: UUID,
    eligible: bool,
) -> None:
    """Existe, `ACTIVE`, del mismo producto global y, al adoptar, elegible (FR-011 paso 6)."""
    ref = catalog.lookup_presentation(presentation_id)

    if not ref.found:
        raise GlobalPresentationNotFoundError(field=GLOBAL_FIELD)

    if ref.status != ACTIVE:
        raise GlobalPresentationInactiveError(field=GLOBAL_FIELD)

    if ref.global_product_id != global_product_id:
        raise GlobalPresentationOfOtherProductError(field=GLOBAL_FIELD)

    if eligible and not ref.eligible_for_adoption:
        raise GlobalPresentationNotEligibleError(field=GLOBAL_FIELD)


class CompanyProductPresentationService:
    """Adopción, mantenimiento, estados y consulta por lotes de presentaciones."""

    def __init__(self, repository, product_repository, catalog_factory) -> None:
        self._repository = repository
        self._products = product_repository
        # Product Catalog se resuelve solo cuando hace falta (no pide el token técnico en vano).
        self._catalog_factory = catalog_factory

    # ---------------------------------------------------------------- adopción

    def adopt(self, company_id: UUID, values: dict[str, Any], *, actor: str):
        """FR-011: entrada → producto → unicidad → elegibilidad → primer uso → persistencia."""
        validate_presentation_flags(
            is_purchasable=values["is_purchasable"],
            is_sellable=values["is_sellable"],
            is_default_purchase=values["is_default_purchase"],
            is_default_sale=values["is_default_sale"],
        )
        product = require_product(self._products, values["company_product_id"], company_id)
        presentation_id = values[GLOBAL_FIELD]

        if self._repository.adoption_exists(product.id, presentation_id):
            raise DuplicatePresentationAdoptionError(field=GLOBAL_FIELD)

        self._check_codes(company_id, values, exclude_id=None)

        catalog: ProductCatalogDirectory = self._catalog_factory()
        _require_global_presentation(
            catalog, presentation_id, global_product_id=product.global_product_id, eligible=True
        )
        # Primer uso síncrono antes de confirmar (FR-011 paso 7): si falla, no se guarda nada.
        catalog.register_first_use(product.global_product_id, presentation_id)

        model = self._repository.build(company_id=company_id, created_by=actor, updated_by=actor, **values)
        self._repository.lock_product(product.id)
        self._clear_new_marks(None, values, actor=actor, company_product_id=product.id)
        return self._repository.add(model, duplicates=self._repository.duplicates, audit=audit_events.spec(audit_events.CREATE_COMPANY_PRODUCT_PRESENTATION, "CompanyProductPresentation", model.company_id))

    # ----------------------------------------------------------- mantenimiento

    def update(self, current, values: dict[str, Any], *, version: int, actor: str):
        """`PUT` en cualquier estado (FR-014): no consulta Product Catalog ni cambia el estado."""
        values = dict(values)

        # Desmarcar la bandera desmarca la predeterminada que ya tenía (FR-014).
        if not values["is_purchasable"] and values["is_default_purchase"] and current.is_default_purchase:
            values["is_default_purchase"] = False

        if not values["is_sellable"] and values["is_default_sale"] and current.is_default_sale:
            values["is_default_sale"] = False

        validate_presentation_flags(
            is_purchasable=values["is_purchasable"],
            is_sellable=values["is_sellable"],
            is_default_purchase=values["is_default_purchase"],
            is_default_sale=values["is_default_sale"],
        )

        for mark in MARKS:
            require_active_for_mark(current.status, marked=values[mark], field=mark)

        self._check_codes(current.company_id, values, exclude_id=current.id)

        self._repository.lock_product(current.company_product_id)
        model = self._repository.load_for_update(current.id, expected_version=version)

        if unchanged(model, values):
            self._repository.release()
            return model

        self._clear_new_marks(model, values, actor=actor)

        for name in EDITABLE_FIELDS:
            setattr(model, name, values[name])

        touch(model, actor)
        return self._repository.save(model, duplicates=self._repository.duplicates, audit=audit_events.spec(audit_events.UPDATE_COMPANY_PRODUCT_PRESENTATION, "CompanyProductPresentation", model.company_id))

    def deactivate(self, current, *, version: int, actor: str):
        """Inactivar retira sus marcas de predeterminada (DS-05); no consulta Product Catalog."""
        model = self._repository.load_for_update(current.id, expected_version=version)
        model.status = next_status(model.status, DEACTIVATE)

        for mark in MARKS:
            setattr(model, mark, False)

        touch(model, actor)
        return self._repository.save(model, duplicates={}, audit=audit_events.spec(audit_events.DEACTIVATE_COMPANY_PRODUCT_PRESENTATION, "CompanyProductPresentation", model.company_id))

    def reactivate(self, current, *, version: int, actor: str):
        """FR-015: producto empresarial `ACTIVE` y presentación global `ACTIVE`; sin primer uso."""
        next_status(current.status, REACTIVATE)
        product = require_product(self._products, current.company_product_id, current.company_id, active=False)

        if product.status != ACTIVE:
            raise CompanyProductInactiveError(field="company_product_id")

        _require_global_presentation(
            self._catalog_factory(),
            current.global_product_presentation_id,
            global_product_id=product.global_product_id,
            eligible=False,
        )

        model = self._repository.load_for_update(current.id, expected_version=version)
        model.status = next_status(model.status, REACTIVATE)
        touch(model, actor)
        return self._repository.save(model, duplicates=self._repository.duplicates, audit=audit_events.spec(audit_events.REACTIVATE_COMPANY_PRODUCT_PRESENTATION, "CompanyProductPresentation", model.company_id))

    # ------------------------------------------------------------------ lotes

    def batch_lookup(
        self,
        ids: list[UUID],
        *,
        identity: RequestIdentity,
        scope: CompanyScopeService,
    ) -> list[BatchItem]:
        """FR-081: 1–100 UUID, duplicados ignorados; ajenos como no encontrados (R-12 de la 007)."""
        unique = list(dict.fromkeys(ids))

        if len(unique) > BATCH_LIMIT:
            raise BatchLimitExceededError(field="ids")

        rows = {row.id: row for row in self._repository.get_many(unique)}

        if not identity.technical_lookup:
            visible = {
                company_id: scope.is_member(company_id)
                for company_id in {row.company_id for row in rows.values()}
            }
            rows = {row_id: row for row_id, row in rows.items() if visible[row.company_id]}

        return [BatchItem(id=item_id, model=rows.get(item_id)) for item_id in unique]

    # -------------------------------------------------------------- internos

    def _check_codes(self, company_id: UUID, values: dict[str, Any], *, exclude_id: UUID | None) -> None:
        if self._repository.code_in_use(company_id, "sku", values["sku"], exclude_id=exclude_id):
            raise DuplicateSkuError(field="sku")

        if self._repository.code_in_use(
            company_id, "internal_code", values["internal_code"], exclude_id=exclude_id
        ):
            raise DuplicateInternalCodeError(field="internal_code")

    def _clear_new_marks(
        self,
        model,
        values: dict[str, Any],
        *,
        actor: str,
        company_product_id: UUID | None = None,
    ) -> None:
        scope_id = company_product_id if model is None else model.company_product_id

        for mark in MARKS:
            if values[mark] and (model is None or not getattr(model, mark)):
                self._repository.clear_product_marks(
                    mark, scope_id, exclude_id=None if model is None else model.id, actor=actor
                )
