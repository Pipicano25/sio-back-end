"""Definiciones de atributo y opciones (FR-038 a FR-040, DS-19)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from product_catalog_service.application import audit_events as audit
from product_catalog_service.application import lifecycle
from product_catalog_service.application.exceptions import (
    DefinitionNotOptionError,
    DuplicateCodeError,
    NotFoundError,
    ReferenceInactiveError,
    ReferenceNotFoundError,
    UnitNotAllowedForDataTypeError,
    ValidationError,
)
from product_catalog_service.application.normalization import (
    normalize_code,
    normalize_name,
    normalize_optional_text,
)
from product_catalog_service.application.simple_catalog import SimpleCatalogService
from product_catalog_service.infrastructure.locks import lock_row
from product_catalog_service.infrastructure.models import (
    GlobalUnitOfMeasureModel,
    ProductAttributeDefinitionModel,
    ProductAttributeOptionModel,
)

ACTIVE = lifecycle.ACTIVE
NUMERIC_TYPES = frozenset({"INTEGER", "DECIMAL"})


def _required_description(value: str | None) -> str:
    description = normalize_optional_text(value)
    if description is None:
        raise ValidationError("La descripción es obligatoria.", field="description")
    return description


class AttributeDefinitionService(SimpleCatalogService[ProductAttributeDefinitionModel]):
    audit_entity = "AttributeDefinition"  # feature 016
    audit_suffix = "ATTRIBUTE_DEFINITION"
    model = ProductAttributeDefinitionModel
    label = "La definición de atributo"
    code_max_length = 80
    name_max_length = 120

    def create(self, *, code: str, name: str, actor: str, **fields: Any) -> ProductAttributeDefinitionModel:
        data_type = fields["data_type"]
        unit_id = fields.get("unit_of_measure_id")

        if unit_id is not None:
            if data_type not in NUMERIC_TYPES:
                raise UnitNotAllowedForDataTypeError(
                    "Solo los atributos INTEGER y DECIMAL admiten unidad de medida."
                )
            unit = self.session.get(GlobalUnitOfMeasureModel, unit_id)
            if unit is None:
                raise ReferenceNotFoundError(f"La unidad de medida {unit_id} no existe.")
            if unit.status != ACTIVE:
                raise ReferenceInactiveError("La unidad de medida está inactiva.")

        return super().create(code=code, name=name, actor=actor, **fields)

    def prepare_fields(self, fields: dict[str, Any]) -> dict[str, Any]:
        prepared = dict(fields)
        if "description" in prepared:
            prepared["description"] = _required_description(prepared["description"])
        return prepared

    # ------------------------------------------------------------------ opciones

    def list_options(self, definition_id: UUID, status: str | None = None) -> list[ProductAttributeOptionModel]:
        self.get(definition_id)
        statement = select(ProductAttributeOptionModel).where(
            ProductAttributeOptionModel.attribute_definition_id == definition_id
        )
        if status is not None:
            statement = statement.where(ProductAttributeOptionModel.status == status)
        return list(
            self.session.execute(
                statement.order_by(ProductAttributeOptionModel.display_order, ProductAttributeOptionModel.code)
            ).scalars()
        )

    def create_option(
        self,
        definition_id: UUID,
        *,
        code: str,
        name: str,
        description: str | None,
        display_order: int,
        actor: str,
    ) -> ProductAttributeOptionModel:
        definition = lock_row(self.session, ProductAttributeDefinitionModel, definition_id, label=self.label)
        self._require_option_definition(definition)

        normalized_code = normalize_code(code, max_length=80)
        option = ProductAttributeOptionModel(
            attribute_definition_id=definition_id,
            code=normalized_code,
            name=normalize_name(name, max_length=120),
            description=normalize_optional_text(description),
            display_order=display_order,
            status=ACTIVE,
        )
        lifecycle.stamp_create(option, actor)
        self.session.add(option)

        audit.track_create(self.session, option, action=audit.CREATE_ATTRIBUTE_OPTION, entity_type="AttributeOption")
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            raise DuplicateCodeError(
                f"La definición ya tiene una opción con el código {normalized_code}."
            ) from None
        return option

    def update_option(
        self,
        definition_id: UUID,
        option_id: UUID,
        *,
        version: int,
        name: str,
        description: str | None,
        display_order: int,
        actor: str,
    ) -> ProductAttributeOptionModel:
        option = self._option(definition_id, option_id, lock=True)
        lifecycle.check_version(option, version)
        option.name = normalize_name(name, max_length=120)
        option.description = normalize_optional_text(description)
        option.display_order = display_order
        lifecycle.stamp_update(option, actor)
        audit.track_update(self.session, option, action=audit.UPDATE_ATTRIBUTE_OPTION, entity_type="AttributeOption")
        self.session.commit()
        return option

    def deactivate_option(self, definition_id: UUID, option_id: UUID, *, version: int, actor: str):
        option = self._option(definition_id, option_id, lock=True)
        lifecycle.deactivate(option, version, actor)
        audit.track_update(self.session, option, action=audit.DEACTIVATE_ATTRIBUTE_OPTION, entity_type="AttributeOption")
        self.session.commit()
        return option

    def reactivate_option(self, definition_id: UUID, option_id: UUID, *, version: int, actor: str):
        option = self._option(definition_id, option_id, lock=True)
        definition = self.get(definition_id)
        if definition.status != ACTIVE:
            raise ReferenceInactiveError("La definición del atributo está inactiva.")
        lifecycle.reactivate(option, version, actor)
        audit.track_update(self.session, option, action=audit.REACTIVATE_ATTRIBUTE_OPTION, entity_type="AttributeOption")
        self.session.commit()
        return option

    def _option(self, definition_id: UUID, option_id: UUID, *, lock: bool = False) -> ProductAttributeOptionModel:
        option = (
            lock_row(self.session, ProductAttributeOptionModel, option_id, label="La opción")
            if lock
            else self.session.get(ProductAttributeOptionModel, option_id)
        )
        if option is None or option.attribute_definition_id != definition_id:
            raise NotFoundError(f"La opción {option_id} no existe en la definición.")
        return option

    @staticmethod
    def _require_option_definition(definition: ProductAttributeDefinitionModel) -> None:
        if definition.data_type != "OPTION":
            raise DefinitionNotOptionError("Solo las definiciones de tipo OPTION admiten opciones.")
        if definition.status != ACTIVE:
            raise ReferenceInactiveError("La definición del atributo está inactiva.")
