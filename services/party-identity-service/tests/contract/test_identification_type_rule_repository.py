"""Pruebas del repositorio de reglas sobre PostgreSQL (RC-03, FR-015, R-09)."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import select

from party_identity_service.application.exceptions import (
    DuplicateActiveRuleError,
    InvalidStatusTransitionError,
)
from party_identity_service.infrastructure.identification_type_rule_repository import (
    SQLAlchemyIdentificationTypeRuleRepository,
)
from party_identity_service.infrastructure.models import IdentificationTypeRuleModel
from tests.conftest import COLOMBIA_ID


@pytest.fixture
def repository(db_session) -> SQLAlchemyIdentificationTypeRuleRepository:
    return SQLAlchemyIdentificationTypeRuleRepository(db_session)


def _create(repository, **overrides):
    values = {
        "party_kind": "PERSON",
        "country_id": COLOMBIA_ID,
        "identification_type": "CITIZEN_ID_MODERN",
        "sigla": "CC",
        "number_pattern": "^[0-9]{10}$",
        "number_pattern_description": "Cédula moderna.",
        "example_value": "1000000000",
        "min_age_years": 18,
        "max_age_years": None,
        "valid_from": None,
        "valid_to": None,
        "actor_id": "admin",
    }
    values.update(overrides)
    return repository.create(**values)


def _new_version(repository, rule, **overrides):
    values = {
        "expected_version": rule.version,
        "number_pattern": "^[0-9]{11}$",
        "number_pattern_description": "Nueva versión.",
        "example_value": None,
        "min_age_years": 18,
        "max_age_years": None,
        "actor_id": "editor",
    }
    values.update(overrides)
    return repository.create_version(rule.id, **values)


def test_only_one_active_rule_per_key(repository) -> None:
    _create(repository)

    with pytest.raises(DuplicateActiveRuleError):
        _create(repository, number_pattern_description="Otra.")


def test_one_active_and_several_historic_rules_are_allowed(repository) -> None:
    first = _create(repository)
    second = _new_version(repository, first)
    third = _new_version(repository, second, number_pattern="^[0-9]{12}$")

    rules = repository.list_all(page=1, page_size=10, identification_type="CITIZEN_ID_MODERN")

    assert rules.total_records == 3
    assert [rule.id for rule in rules.items if rule.is_active] == [third.id]


def test_create_version_closes_current_and_creates_successor(repository, db_session) -> None:
    rule = _create(repository)

    successor = _new_version(repository, rule)
    previous = db_session.get(IdentificationTypeRuleModel, rule.id)

    assert successor.is_active is True
    assert successor.number_pattern == "^[0-9]{11}$"
    assert successor.created_by == "editor"
    assert previous.is_active is False
    assert previous.valid_to is not None
    assert previous.valid_to <= successor.valid_from + timedelta(seconds=1)


def test_failed_version_leaves_current_rule_intact(repository, db_session) -> None:
    rule = _create(repository)

    with patch.object(db_session, "commit", side_effect=RuntimeError("fallo al insertar")):
        with pytest.raises(RuntimeError):
            _new_version(repository, rule)
    db_session.rollback()

    stored = db_session.get(IdentificationTypeRuleModel, rule.id, populate_existing=True)
    count = len(db_session.scalars(select(IdentificationTypeRuleModel.id)).all())

    assert stored.is_active is True
    assert stored.valid_to is None
    assert count == 1


def test_historic_rule_cannot_get_new_versions(repository) -> None:
    rule = _create(repository)
    retired = repository.deactivate(rule.id, expected_version=1, actor_id="admin")

    with pytest.raises(InvalidStatusTransitionError):
        _new_version(repository, retired)


def test_deactivate_sets_valid_to_only_when_already_effective(repository) -> None:
    current = _create(repository)
    future = _create(
        repository,
        identification_type="FUTURE_TYPE",
        valid_from=datetime.now(timezone.utc) + timedelta(days=30),
    )

    retired = repository.deactivate(current.id, expected_version=1, actor_id="admin")
    retired_future = repository.deactivate(future.id, expected_version=1, actor_id="admin")

    assert retired.is_active is False
    assert retired.valid_to is not None
    assert retired_future.is_active is False
    assert retired_future.valid_to is None


def test_future_rule_is_not_active_for_validation(repository) -> None:
    _create(
        repository,
        identification_type="FUTURE_TYPE",
        sigla="FT",
        valid_from=datetime.now(timezone.utc) + timedelta(days=30),
    )

    assert repository.list_active_rules_by_sigla(party_kind="PERSON", country_id=COLOMBIA_ID, sigla="FT") == []


def test_expired_rule_is_not_active_for_validation(repository) -> None:
    start = datetime.now(timezone.utc) - timedelta(days=10)
    _create(
        repository,
        identification_type="EXPIRED_TYPE",
        sigla="EX",
        valid_from=start,
        valid_to=start + timedelta(days=1),
    )

    assert repository.list_active_rules_by_sigla(party_kind="PERSON", country_id=COLOMBIA_ID, sigla="EX") == []
