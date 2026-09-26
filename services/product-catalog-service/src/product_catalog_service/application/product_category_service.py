"""Clasificación del producto en categorías (FR-034 a FR-037, RC-04, DS-12)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from product_catalog_service.application import lifecycle
from product_catalog_service.application.exceptions import (
    DuplicateAssociationError,
    NewPrimaryRequiredError,
    NotFoundError,
    ReferenceInactiveError,
    ReferenceNotFoundError,
    ValidationError,
)
from product_catalog_service.application.product_service import ensure_product_active_for_dependents
from product_catalog_service.infrastructure.locks import lock_product
from product_catalog_service.infrastructure.models import (
    GlobalCategoryModel,
    GlobalProductCategoryModel,
)

ACTIVE = lifecycle.ACTIVE
INACTIVE = lifecycle.INACTIVE


class ProductCategoryService:
    """Todas las operaciones bloquean primero la fila del producto (R-10)."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self, product_id: UUID, status: str | None = None) -> list[GlobalProductCategoryModel]:
        self._product_exists(product_id)
        statement = select(GlobalProductCategoryModel).where(
            GlobalProductCategoryModel.global_product_id == product_id
        )
        if status is not None:
            statement = statement.where(GlobalProductCategoryModel.status == status)
        return list(
            self.session.execute(
                statement.order_by(GlobalProductCategoryModel.is_primary.desc(), GlobalProductCategoryModel.created_at)
            ).scalars()
        )

    def assign(self, product_id: UUID, category_id: UUID, actor: str) -> tuple[GlobalProductCategoryModel, bool]:
        """Asigna o reactiva la pareja. Devuelve (asociación, creada)."""
        product = lock_product(self.session, product_id)
        ensure_product_active_for_dependents(product)

        category = self.session.get(GlobalCategoryModel, category_id)
        if category is None:
            raise ReferenceNotFoundError(f"La categoría {category_id} no existe.")
        if category.status != ACTIVE:
            raise ReferenceInactiveError("La categoría está inactiva y no puede asignarse.")

        association = self._pair(product_id, category_id)
        created = association is None

        if association is not None and association.status == ACTIVE:
            raise DuplicateAssociationError("La categoría ya está asignada al producto.")

        make_primary = self._current_primary(product_id) is None

        if association is None:
            association = GlobalProductCategoryModel(
                global_product_id=product_id,
                global_category_id=category_id,
                is_primary=make_primary,
                status=ACTIVE,
            )
            lifecycle.stamp_create(association, actor)
            self.session.add(association)
        else:
            association.status = ACTIVE
            association.is_primary = make_primary
            lifecycle.stamp_update(association, actor)

        self.session.commit()
        return association, created

    def set_primary(self, product_id: UUID, association_id: UUID, version: int, actor: str) -> None:
        product = lock_product(self.session, product_id)
        ensure_product_active_for_dependents(product)

        association = self._association(product_id, association_id)
        lifecycle.check_version(association, version)
        if association.status != ACTIVE:
            raise ReferenceInactiveError("Solo una clasificación vigente puede ser principal.")

        if association.is_primary:
            return

        current = self._current_primary(product_id)
        if current is not None:
            current.is_primary = False
            lifecycle.stamp_update(current, actor)
            self.session.flush()

        association.is_primary = True
        lifecycle.stamp_update(association, actor)
        self.session.commit()

    def deactivate(
        self,
        product_id: UUID,
        association_id: UUID,
        version: int,
        actor: str,
        new_primary_association_id: UUID | None = None,
    ) -> GlobalProductCategoryModel:
        lock_product(self.session, product_id)
        association = self._association(product_id, association_id)
        lifecycle.check_version(association, version)

        if association.status == INACTIVE:
            return association

        others = [
            item
            for item in self._active(product_id)
            if item.id != association.id
        ]

        new_primary = None
        if association.is_primary and others:
            if new_primary_association_id is None:
                raise NewPrimaryRequiredError(
                    "Indique la nueva categoría principal en new_primary_association_id."
                )
            new_primary = next((item for item in others if item.id == new_primary_association_id), None)
            if new_primary is None:
                raise ValidationError(
                    "La nueva principal debe ser otra clasificación vigente del producto.",
                    field="new_primary_association_id",
                )

        lifecycle.deactivate(association, version, actor)
        self.session.flush()

        if new_primary is not None:
            new_primary.is_primary = True
            lifecycle.stamp_update(new_primary, actor)

        self.session.commit()
        return association

    # ---------------------------------------------------------------- utilidades

    def _product_exists(self, product_id: UUID) -> None:
        from product_catalog_service.infrastructure.models import GlobalProductModel

        if self.session.get(GlobalProductModel, product_id) is None:
            raise NotFoundError(f"El producto {product_id} no existe.")

    def _pair(self, product_id: UUID, category_id: UUID) -> GlobalProductCategoryModel | None:
        return self.session.execute(
            select(GlobalProductCategoryModel).where(
                GlobalProductCategoryModel.global_product_id == product_id,
                GlobalProductCategoryModel.global_category_id == category_id,
            )
        ).scalar_one_or_none()

    def _association(self, product_id: UUID, association_id: UUID) -> GlobalProductCategoryModel:
        association = self.session.get(GlobalProductCategoryModel, association_id)
        if association is None or association.global_product_id != product_id:
            raise NotFoundError(f"La clasificación {association_id} no existe en el producto.")
        return association

    def _active(self, product_id: UUID) -> list[GlobalProductCategoryModel]:
        return list(
            self.session.execute(
                select(GlobalProductCategoryModel).where(
                    GlobalProductCategoryModel.global_product_id == product_id,
                    GlobalProductCategoryModel.status == ACTIVE,
                )
            ).scalars()
        )

    def _current_primary(self, product_id: UUID) -> GlobalProductCategoryModel | None:
        return next((item for item in self._active(product_id) if item.is_primary), None)
