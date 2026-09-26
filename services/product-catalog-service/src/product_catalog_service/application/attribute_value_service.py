"""Valores de atributo por producto (FR-044 a FR-048, DS-08, DS-09)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from product_catalog_service.application import lifecycle
from product_catalog_service.application.exceptions import (
    AttributeNotApplicableError,
    NotFoundError,
    OptionNotInDefinitionError,
    ReferenceInactiveError,
    ValidationError,
    ValueOutOfClassificationError,
    ValueTypeMismatchError,
)
from product_catalog_service.application.product_service import ensure_product_active_for_dependents
from product_catalog_service.domain.attribute_value import (
    VALUE_FIELDS,
    ValueTypeMismatch,
    validate_typed_value,
)
from product_catalog_service.infrastructure.category_attribute_repository import (
    applicable_definition_ids,
    applicable_for_product,
)
from product_catalog_service.infrastructure.locks import lock_product
from product_catalog_service.infrastructure.models import (
    GlobalProductAttributeValueModel,
    GlobalProductModel,
    ProductAttributeDefinitionModel,
    ProductAttributeOptionModel,
)

ACTIVE = lifecycle.ACTIVE


@dataclass(frozen=True, slots=True)
class ValueView:
    value: GlobalProductAttributeValueModel
    out_of_classification: bool


class AttributeValueService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self, product_id: UUID) -> list[ValueView]:
        if self.session.get(GlobalProductModel, product_id) is None:
            raise NotFoundError(f"El producto {product_id} no existe.")
        applicable = applicable_definition_ids(self.session, product_id)
        values = self.session.execute(
            select(GlobalProductAttributeValueModel)
            .where(GlobalProductAttributeValueModel.global_product_id == product_id)
            .order_by(GlobalProductAttributeValueModel.created_at)
        ).scalars()
        return [ValueView(value, value.attribute_definition_id not in applicable) for value in values]

    def set_value(
        self,
        product_id: UUID,
        definition_id: UUID,
        *,
        payload: dict[str, Any],
        version: int | None,
        actor: str,
    ) -> tuple[ValueView, bool]:
        """Registra o reemplaza el valor. Devuelve (vista, creado)."""
        product = lock_product(self.session, product_id)
        ensure_product_active_for_dependents(product)

        definition = self.session.get(ProductAttributeDefinitionModel, definition_id)
        if definition is None:
            raise NotFoundError(f"La definición de atributo {definition_id} no existe.")
        if definition.status != ACTIVE:
            raise ReferenceInactiveError("La definición de atributo está inactiva.")

        existing = self._value(product_id, definition_id)

        if existing is not None and definition_id not in applicable_definition_ids(self.session, product_id):
            raise ValueOutOfClassificationError(
                "El valor está fuera de clasificación: vuelva a asignar una categoría que use el atributo."
            )

        applicable = {item.definition.id for item in applicable_for_product(self.session, product_id)}
        if definition_id not in applicable:
            raise AttributeNotApplicableError(
                "El atributo no es aplicable por ninguna categoría vigente del producto."
            )

        try:
            field, value = validate_typed_value(definition.data_type, payload)
        except ValueTypeMismatch as exc:
            raise ValueTypeMismatchError(str(exc)) from None

        if field == "option_id":
            self._require_option(definition_id, value)

        created = existing is None
        if created:
            existing = GlobalProductAttributeValueModel(
                global_product_id=product_id,
                attribute_definition_id=definition_id,
            )
            lifecycle.stamp_create(existing, actor)
            self.session.add(existing)
        else:
            if version is None:
                raise ValidationError("Para reemplazar un valor debe enviar la versión esperada.", field="version")
            lifecycle.check_version(existing, version)
            lifecycle.stamp_update(existing, actor)

        for name in VALUE_FIELDS:
            setattr(existing, name, value if name == field else None)

        self.session.commit()
        self.session.refresh(existing)
        return ValueView(existing, False), created

    def remove_value(self, product_id: UUID, definition_id: UUID, *, version: int) -> None:
        """Retira el valor con eliminación física (DS-08; confirmado en /speckit-analyze)."""
        lock_product(self.session, product_id)
        existing = self._value(product_id, definition_id)
        if existing is None:
            raise NotFoundError("El producto no tiene valor para ese atributo.")
        lifecycle.check_version(existing, version)
        self.session.delete(existing)
        self.session.commit()

    # ---------------------------------------------------------------- utilidades

    def _value(self, product_id: UUID, definition_id: UUID) -> GlobalProductAttributeValueModel | None:
        return self.session.execute(
            select(GlobalProductAttributeValueModel).where(
                GlobalProductAttributeValueModel.global_product_id == product_id,
                GlobalProductAttributeValueModel.attribute_definition_id == definition_id,
            )
        ).scalar_one_or_none()

    def _require_option(self, definition_id: UUID, option_id: UUID) -> None:
        option = self.session.get(ProductAttributeOptionModel, option_id)
        if option is None or option.attribute_definition_id != definition_id or option.status != ACTIVE:
            raise OptionNotInDefinitionError(
                "La opción no existe, está inactiva o no pertenece a la definición del atributo."
            )
