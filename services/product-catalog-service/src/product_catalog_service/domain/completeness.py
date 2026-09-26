"""Completitud y elegibilidad del producto (FR-032, FR-074, RN-15, R-14).

Funciones puras y sin E/S: reciben una instantánea del producto y devuelven un
indicador derivado que nunca se almacena (DS-01).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

ACTIVE = "ACTIVE"

# Campo de valor que corresponde a cada tipo de dato.
VALUE_FIELD_BY_DATA_TYPE = {
    "TEXT": "text_value",
    "INTEGER": "integer_value",
    "DECIMAL": "decimal_value",
    "BOOLEAN": "boolean_value",
    "DATE": "date_value",
    "OPTION": "option_id",
}

MISSING_MINIMUM_DATA = "MISSING_MINIMUM_DATA"
BASE_UNIT_NOT_FOUND = "BASE_UNIT_NOT_FOUND"
NO_ACTIVE_CATEGORY = "NO_ACTIVE_CATEGORY"
NO_PRIMARY_CATEGORY = "NO_PRIMARY_CATEGORY"
MISSING_REQUIRED_ATTRIBUTE = "MISSING_REQUIRED_ATTRIBUTE"
INCONSISTENT_REQUIRED_VALUE = "INCONSISTENT_REQUIRED_VALUE"
NO_ACTIVE_PRESENTATION = "NO_ACTIVE_PRESENTATION"


@dataclass(frozen=True, slots=True)
class ValueSnapshot:
    """Valor registrado de un atributo."""

    value_id: UUID
    definition_id: UUID
    filled_field: str | None
    option_definition_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class ProductSnapshot:
    """Datos del producto necesarios para evaluar la completitud.

    - `active_category_count` / `active_primary_count`: asociaciones
      producto–categoría `ACTIVE`, sin importar el estado de la categoría (RN-15).
    - `required_definitions`: definiciones `ACTIVE` obligatorias por alguna
      asociación categoría–atributo vigente de esas categorías (sin herencia),
      con su tipo de dato.
    - `applicable_definition_ids`: definiciones con asociación vigente en esas
      categorías (para detectar valores fuera de clasificación).
    """

    product_id: UUID
    status: str
    product_type: str | None
    canonical_name: str | None
    base_unit_id: UUID | None
    base_unit_exists: bool
    active_category_count: int
    active_primary_count: int
    required_definitions: dict[UUID, str] = field(default_factory=dict)
    applicable_definition_ids: frozenset[UUID] = frozenset()
    values: tuple[ValueSnapshot, ...] = ()
    active_presentation_count: int = 0


@dataclass(frozen=True, slots=True)
class ProductCompleteness:
    """Resultado derivado de la evaluación."""

    is_complete: bool
    issues: tuple[str, ...]
    missing_attribute_definition_ids: tuple[UUID, ...]
    out_of_classification_value_ids: tuple[UUID, ...]


def _value_is_consistent(value: ValueSnapshot, data_type: str) -> bool:
    expected_field = VALUE_FIELD_BY_DATA_TYPE.get(data_type)
    if expected_field is None or value.filled_field != expected_field:
        return False

    if data_type == "OPTION":
        return value.option_definition_id == value.definition_id

    return True


def evaluate_completeness(snapshot: ProductSnapshot) -> ProductCompleteness:
    """Evalúa las seis condiciones de FR-032."""
    issues: list[str] = []

    # 1. Datos mínimos.
    if not snapshot.product_type or not (snapshot.canonical_name or "").strip() or snapshot.base_unit_id is None:
        issues.append(MISSING_MINIMUM_DATA)

    # 2. Unidad base existente (su inactivación posterior no afecta, DS-20).
    if snapshot.base_unit_id is not None and not snapshot.base_unit_exists:
        issues.append(BASE_UNIT_NOT_FOUND)

    # 3. Al menos una categoría vigente y exactamente una principal.
    if snapshot.active_category_count == 0:
        issues.append(NO_ACTIVE_CATEGORY)
    elif snapshot.active_primary_count != 1:
        issues.append(NO_PRIMARY_CATEGORY)

    # 4 y 5. Atributos obligatorios con valor consistente.
    values_by_definition = {value.definition_id: value for value in snapshot.values}
    missing: list[UUID] = []
    inconsistent = False

    for definition_id, data_type in sorted(snapshot.required_definitions.items(), key=lambda item: str(item[0])):
        value = values_by_definition.get(definition_id)
        if value is None:
            missing.append(definition_id)
        elif not _value_is_consistent(value, data_type):
            inconsistent = True

    if missing:
        issues.append(MISSING_REQUIRED_ATTRIBUTE)
    if inconsistent:
        issues.append(INCONSISTENT_REQUIRED_VALUE)

    # 6. Al menos una presentación ACTIVE.
    if snapshot.active_presentation_count == 0:
        issues.append(NO_ACTIVE_PRESENTATION)

    out_of_classification = tuple(
        value.value_id
        for value in snapshot.values
        if value.definition_id not in snapshot.applicable_definition_ids
    )

    return ProductCompleteness(
        is_complete=not issues,
        issues=tuple(issues),
        missing_attribute_definition_ids=tuple(missing),
        out_of_classification_value_ids=out_of_classification,
    )


def is_eligible(status: str, completeness: ProductCompleteness) -> bool:
    """Elegible para nuevas adopciones: `ACTIVE` y completo (FR-074)."""
    return status == ACTIVE and completeness.is_complete


def is_presentation_eligible(
    presentation_status: str,
    product_status: str,
    completeness: ProductCompleteness,
) -> bool:
    """Presentación elegible: `ACTIVE` y su producto elegible (FR-074)."""
    return presentation_status == ACTIVE and is_eligible(product_status, completeness)
