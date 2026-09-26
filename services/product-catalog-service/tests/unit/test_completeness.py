"""Completitud derivada y elegibilidad (RC-16, FR-032, FR-074, DS-20, RN-15)."""

from dataclasses import replace
from uuid import uuid4

from product_catalog_service.domain.completeness import (
    BASE_UNIT_NOT_FOUND,
    INCONSISTENT_REQUIRED_VALUE,
    MISSING_MINIMUM_DATA,
    MISSING_REQUIRED_ATTRIBUTE,
    NO_ACTIVE_CATEGORY,
    NO_ACTIVE_PRESENTATION,
    NO_PRIMARY_CATEGORY,
    ProductSnapshot,
    ValueSnapshot,
    evaluate_completeness,
    is_eligible,
    is_presentation_eligible,
)

FAT = uuid4()
CERT = uuid4()
COLOR = uuid4()


def _complete() -> ProductSnapshot:
    return ProductSnapshot(
        product_id=uuid4(),
        status="ACTIVE",
        product_type="GOOD",
        canonical_name="Leche entera",
        base_unit_id=uuid4(),
        base_unit_exists=True,
        active_category_count=1,
        active_primary_count=1,
        required_definitions={FAT: "DECIMAL"},
        applicable_definition_ids=frozenset({FAT}),
        values=(ValueSnapshot(uuid4(), FAT, "decimal_value"),),
        active_presentation_count=1,
    )


def test_complete_product_is_eligible() -> None:
    result = evaluate_completeness(_complete())
    assert result.is_complete
    assert result.issues == ()
    assert is_eligible("ACTIVE", result)


def test_inactive_complete_product_is_not_eligible() -> None:
    result = evaluate_completeness(_complete())
    assert not is_eligible("INACTIVE", result)


def test_missing_minimum_data() -> None:
    result = evaluate_completeness(replace(_complete(), canonical_name="  "))
    assert result.issues == (MISSING_MINIMUM_DATA,)


def test_base_unit_not_found() -> None:
    result = evaluate_completeness(replace(_complete(), base_unit_exists=False))
    assert result.issues == (BASE_UNIT_NOT_FOUND,)


def test_inactive_base_unit_still_exists_so_product_stays_complete() -> None:
    # DS-20: la instantánea solo pregunta por existencia, no por estado.
    assert evaluate_completeness(replace(_complete(), base_unit_exists=True)).is_complete


def test_no_active_category() -> None:
    result = evaluate_completeness(
        replace(_complete(), active_category_count=0, active_primary_count=0, required_definitions={})
    )
    assert result.issues == (NO_ACTIVE_CATEGORY,)


def test_no_primary_category() -> None:
    result = evaluate_completeness(replace(_complete(), active_category_count=2, active_primary_count=0))
    assert result.issues == (NO_PRIMARY_CATEGORY,)


def test_required_attributes_from_all_categories_participate() -> None:
    snapshot = replace(
        _complete(),
        required_definitions={FAT: "DECIMAL", CERT: "TEXT"},
        applicable_definition_ids=frozenset({FAT, CERT}),
    )
    result = evaluate_completeness(snapshot)
    assert result.issues == (MISSING_REQUIRED_ATTRIBUTE,)
    assert result.missing_attribute_definition_ids == (CERT,)


def test_inconsistent_required_value() -> None:
    snapshot = replace(_complete(), values=(ValueSnapshot(uuid4(), FAT, "text_value"),))
    assert evaluate_completeness(snapshot).issues == (INCONSISTENT_REQUIRED_VALUE,)


def test_option_value_must_belong_to_definition() -> None:
    snapshot = replace(
        _complete(),
        required_definitions={COLOR: "OPTION"},
        applicable_definition_ids=frozenset({COLOR}),
        values=(ValueSnapshot(uuid4(), COLOR, "option_id", option_definition_id=uuid4()),),
    )
    assert evaluate_completeness(snapshot).issues == (INCONSISTENT_REQUIRED_VALUE,)


def test_no_active_presentation() -> None:
    result = evaluate_completeness(replace(_complete(), active_presentation_count=0))
    assert result.issues == (NO_ACTIVE_PRESENTATION,)


def test_out_of_classification_value_is_only_an_observation() -> None:
    stray = ValueSnapshot(uuid4(), uuid4(), "text_value")
    snapshot = replace(_complete(), values=(*_complete().values, stray))
    result = evaluate_completeness(snapshot)
    assert result.is_complete
    assert result.out_of_classification_value_ids == (stray.value_id,)


def test_presentation_eligibility() -> None:
    result = evaluate_completeness(_complete())
    assert is_presentation_eligible("ACTIVE", "ACTIVE", result)
    assert not is_presentation_eligible("INACTIVE", "ACTIVE", result)
    assert not is_presentation_eligible("ACTIVE", "INACTIVE", result)
