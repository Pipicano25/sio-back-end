"""Presentaciones del producto (FR-049 a FR-054, FR-050a, DS-06, DS-10)."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from product_catalog_service.application import audit_events as audit
from product_catalog_service.application import lifecycle
from product_catalog_service.application.exceptions import (
    BasePresentationExistsError,
    BaseQuantityMustBeOneError,
    DuplicateCodeError,
    NotFoundError,
    PresentationLockedByFirstUseError,
    ReferenceInactiveError,
    ReferenceNotFoundError,
    ValidationError,
)
from product_catalog_service.application.normalization import normalize_code, normalize_name
from product_catalog_service.application.product_service import ensure_product_active_for_dependents
from product_catalog_service.infrastructure.locks import lock_product
from product_catalog_service.infrastructure.models import (
    GlobalPackagingTypeModel,
    GlobalProductModel,
    GlobalProductPresentationModel,
    GlobalUnitOfMeasureModel,
)

ACTIVE = lifecycle.ACTIVE
MATERIAL_FIELDS = ("packaging_type_id", "base_quantity", "content_quantity", "content_unit_id")


def _check_numeric(value: Decimal, *, field: str, integer_digits: int, decimals: int) -> None:
    sign, digits, exponent = value.as_tuple()
    places = max(0, -exponent)
    whole = max(0, len(digits) + exponent)
    if places > decimals or whole > integer_digits:
        raise ValidationError(
            f"{field} admite hasta {integer_digits} dígitos enteros y {decimals} decimales.",
            field=field,
        )


class PresentationService:
    def __init__(self, session: Session) -> None:
        self.session = session

    # ------------------------------------------------------------------ lectura

    def list(self, product_id: UUID, status: str | None = None) -> list[GlobalProductPresentationModel]:
        if self.session.get(GlobalProductModel, product_id) is None:
            raise NotFoundError(f"El producto {product_id} no existe.")
        statement = select(GlobalProductPresentationModel).where(
            GlobalProductPresentationModel.global_product_id == product_id
        )
        if status is not None:
            statement = statement.where(GlobalProductPresentationModel.status == status)
        return list(
            self.session.execute(
                statement.order_by(GlobalProductPresentationModel.display_order, GlobalProductPresentationModel.code)
            ).scalars()
        )

    def get(self, presentation_id: UUID) -> GlobalProductPresentationModel:
        presentation = self.session.get(GlobalProductPresentationModel, presentation_id)
        if presentation is None:
            raise NotFoundError(f"La presentación {presentation_id} no existe.")
        return presentation

    # ---------------------------------------------------------------- escritura

    def create(
        self,
        product_id: UUID,
        *,
        code: str,
        name: str,
        packaging_type_id: UUID | None,
        base_quantity: Decimal,
        content_quantity: Decimal | None,
        content_unit_id: UUID | None,
        display_order: int,
        is_base: bool,
        actor: str,
    ) -> GlobalProductPresentationModel:
        product = lock_product(self.session, product_id)
        ensure_product_active_for_dependents(product)

        normalized_code = normalize_code(code, max_length=60)
        exists = self.session.execute(
            select(GlobalProductPresentationModel.id).where(
                GlobalProductPresentationModel.global_product_id == product_id,
                GlobalProductPresentationModel.code == normalized_code,
            )
        ).first()
        if exists is not None:
            raise DuplicateCodeError(f"El producto ya tiene una presentación con el código {normalized_code}.")

        self._validate_material(packaging_type_id, base_quantity, content_quantity, content_unit_id)
        self._validate_base(product_id, None, is_base, base_quantity)

        presentation = GlobalProductPresentationModel(
            global_product_id=product_id,
            code=normalized_code,
            name=normalize_name(name, max_length=160),
            packaging_type_id=packaging_type_id,
            base_quantity=base_quantity,
            content_quantity=content_quantity,
            content_unit_id=content_unit_id,
            display_order=display_order,
            is_base=is_base,
            status=ACTIVE,
        )
        lifecycle.stamp_create(presentation, actor)
        self.session.add(presentation)
        audit.track_create(self.session, presentation, action=audit.CREATE_PRODUCT_PRESENTATION, entity_type="ProductPresentation")
        self.session.commit()
        self.session.refresh(presentation)
        return presentation

    def update(
        self,
        presentation_id: UUID,
        *,
        version: int,
        name: str,
        display_order: int,
        packaging_type_id: UUID | None,
        base_quantity: Decimal,
        content_quantity: Decimal | None,
        content_unit_id: UUID | None,
        is_base: bool,
        actor: str,
    ) -> GlobalProductPresentationModel:
        presentation = self.get(presentation_id)
        product = lock_product(self.session, presentation.global_product_id)
        ensure_product_active_for_dependents(product)
        self.session.refresh(presentation, with_for_update=True)
        lifecycle.check_version(presentation, version)

        requested = {
            "packaging_type_id": packaging_type_id,
            "base_quantity": base_quantity,
            "content_quantity": content_quantity,
            "content_unit_id": content_unit_id,
        }
        changed = [
            field
            for field in MATERIAL_FIELDS
            if not _same(getattr(presentation, field), requested[field])
        ]

        if changed and presentation.first_used_at is not None:
            raise PresentationLockedByFirstUseError(
                "La presentación tiene uso histórico: registre una presentación nueva para cambiar "
                f"{', '.join(changed)}."
            )

        if changed:
            self._validate_material(
                packaging_type_id,
                base_quantity,
                content_quantity,
                content_unit_id,
                check_references={field for field in changed if field.endswith("_id")},
            )

        if presentation.status != ACTIVE and is_base:
            raise ValidationError("Solo una presentación activa puede ser la base.", field="is_base")
        self._validate_base(presentation.global_product_id, presentation.id, is_base, base_quantity)

        for field, value in requested.items():
            setattr(presentation, field, value)
        presentation.name = normalize_name(name, max_length=160)
        presentation.display_order = display_order
        presentation.is_base = is_base
        lifecycle.stamp_update(presentation, actor)
        audit.track_update(self.session, presentation, action=audit.UPDATE_PRODUCT_PRESENTATION, entity_type="ProductPresentation")
        self.session.commit()
        self.session.refresh(presentation)
        return presentation

    def deactivate(self, presentation_id: UUID, *, version: int, actor: str) -> GlobalProductPresentationModel:
        presentation = self.get(presentation_id)
        lock_product(self.session, presentation.global_product_id)
        self.session.refresh(presentation, with_for_update=True)
        lifecycle.deactivate(presentation, version, actor)
        audit.track_update(self.session, presentation, action=audit.DEACTIVATE_PRODUCT_PRESENTATION, entity_type="ProductPresentation")
        self.session.commit()
        return presentation

    def reactivate(self, presentation_id: UUID, *, version: int, actor: str) -> GlobalProductPresentationModel:
        presentation = self.get(presentation_id)
        product = lock_product(self.session, presentation.global_product_id)
        ensure_product_active_for_dependents(product)
        self.session.refresh(presentation, with_for_update=True)
        lifecycle.reactivate(presentation, version, actor)
        audit.track_update(self.session, presentation, action=audit.REACTIVATE_PRODUCT_PRESENTATION, entity_type="ProductPresentation")
        self.session.commit()
        return presentation

    # ---------------------------------------------------------------- utilidades

    def _validate_material(
        self,
        packaging_type_id: UUID | None,
        base_quantity: Decimal,
        content_quantity: Decimal | None,
        content_unit_id: UUID | None,
        *,
        check_references: set[str] | None = None,
    ) -> None:
        """Valida cantidades y contenido; las referencias solo si se asignan o cambian."""
        if base_quantity <= 0:
            raise ValidationError("base_quantity debe ser mayor que cero.", field="base_quantity")
        _check_numeric(base_quantity, field="base_quantity", integer_digits=10, decimals=8)

        if (content_quantity is None) != (content_unit_id is None):
            raise ValidationError(
                "content_quantity y content_unit_id deben informarse juntos.",
                field="content_quantity",
            )

        if content_quantity is not None:
            if content_quantity <= 0:
                raise ValidationError("content_quantity debe ser mayor que cero.", field="content_quantity")
            _check_numeric(content_quantity, field="content_quantity", integer_digits=14, decimals=4)

        references = check_references if check_references is not None else {"packaging_type_id", "content_unit_id"}
        if "packaging_type_id" in references:
            self._require_active(GlobalPackagingTypeModel, packaging_type_id, "El tipo de empaque")
        if "content_unit_id" in references:
            self._require_active(GlobalUnitOfMeasureModel, content_unit_id, "La unidad de contenido")

    def _validate_base(
        self,
        product_id: UUID,
        presentation_id: UUID | None,
        is_base: bool,
        base_quantity: Decimal,
    ) -> None:
        if not is_base:
            return

        if base_quantity != 1:
            raise BaseQuantityMustBeOneError("La presentación base debe tener base_quantity igual a 1.")

        statement = (
            select(GlobalProductPresentationModel.id).where(
                GlobalProductPresentationModel.global_product_id == product_id,
                GlobalProductPresentationModel.is_base.is_(True),
                GlobalProductPresentationModel.status == ACTIVE,
            )
        )
        if presentation_id is not None:
            statement = statement.where(GlobalProductPresentationModel.id != presentation_id)
        other = self.session.execute(statement).first()
        if other is not None:
            raise BasePresentationExistsError("El producto ya tiene una presentación base vigente.")

    def _require_active(self, model, entity_id: UUID | None, label: str) -> None:
        if entity_id is None:
            return
        status = self.session.execute(select(model.status).where(model.id == entity_id)).scalar_one_or_none()
        if status is None:
            raise ReferenceNotFoundError(f"{label} {entity_id} no existe.")
        if status != ACTIVE:
            raise ReferenceInactiveError(f"{label} está inactivo y no puede asignarse.")


def _same(current, requested) -> bool:
    if current is None or requested is None:
        return current is None and requested is None
    if isinstance(current, Decimal) or isinstance(requested, Decimal):
        return Decimal(current) == Decimal(requested)
    return current == requested
