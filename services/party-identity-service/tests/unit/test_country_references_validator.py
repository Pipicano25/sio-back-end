"""Validador `country_id` de reglas ⊆ países de Geography (G-017-01), con el doble de Geography."""

from uuid import uuid4

import pytest

from party_identity_service.application.exceptions import DependencyUnavailableError
from party_identity_service.integrity.country_references import check_rule_country_references
from tests.conftest import COLOMBIA_ID


def test_no_orphans_when_every_country_exists(fake_countries) -> None:
    rules = [(uuid4(), COLOMBIA_ID) for _ in range(8)]

    report = check_rule_country_references(rules, fake_countries)

    assert report.checked_rules == 8
    assert report.rules_by_country == {COLOMBIA_ID: 8}
    assert report.orphan_count == 0
    assert fake_countries.exists_calls == 1  # una consulta por país distinto


def test_orphans_are_reported_by_country(fake_countries) -> None:
    missing = uuid4()
    orphan_ids = sorted((uuid4() for _ in range(3)), key=str)
    rules = [(uuid4(), COLOMBIA_ID)] + [(rule_id, missing) for rule_id in orphan_ids]

    report = check_rule_country_references(rules, fake_countries)

    assert report.orphan_count == 3
    assert report.orphans == {missing: orphan_ids}


def test_geography_unavailable_gives_no_partial_result(fake_countries) -> None:
    fake_countries.mode = "unavailable"

    with pytest.raises(DependencyUnavailableError):
        check_rule_country_references([(uuid4(), COLOMBIA_ID)], fake_countries)
