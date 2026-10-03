"""Pruebas del `seed` en sus dos modos (RC-08, SC-006, FR-016, FR-017)."""

from uuid import uuid4

import pytest
from sqlalchemy import func, select, text

from party_identity_service.application.exceptions import (
    CountryNotFoundError,
    DependencyUnavailableError,
)
from party_identity_service.infrastructure.models import IdentificationTypeRuleModel
from party_identity_service.seed import __main__ as seed_main
from party_identity_service.seed.constants import SEED_ACTOR
from party_identity_service.seed.data import COLOMBIAN_RULES
from party_identity_service.seed.loader import load_seed
from tests.conftest import COLOMBIA_ID


def _count(session) -> int:
    return session.scalar(select(func.count()).select_from(IdentificationTypeRuleModel))


def test_explicit_mode_creates_rules_without_geography(db_session, fake_countries) -> None:
    stats = load_seed(db_session, country_id=COLOMBIA_ID)

    assert stats.mode == "explicit"
    assert stats.created == len(COLOMBIAN_RULES) == 8
    assert fake_countries.calls == []
    rules = db_session.scalars(select(IdentificationTypeRuleModel)).all()
    assert {rule.country_id for rule in rules} == {COLOMBIA_ID}
    assert {rule.created_by for rule in rules} == {SEED_ACTOR}
    assert all(rule.is_active for rule in rules)


def test_geography_mode_resolves_col(db_session, fake_countries) -> None:
    stats = load_seed(db_session, country_directory=fake_countries)

    assert stats.mode == "geography"
    assert stats.country_id == COLOMBIA_ID
    assert fake_countries.calls == [("find_id_by_iso3", "COL")]
    assert _count(db_session) == 8


def test_second_run_is_idempotent(db_session, fake_countries) -> None:
    load_seed(db_session, country_directory=fake_countries)

    stats = load_seed(db_session, country_directory=fake_countries)

    assert stats.created == 0
    assert stats.skipped == 8
    assert _count(db_session) == 8


@pytest.mark.parametrize("mode", ["unavailable", "denied"])
def test_geography_unavailable_writes_nothing(db_session, fake_countries, mode) -> None:
    fake_countries.mode = mode

    with pytest.raises(DependencyUnavailableError):
        load_seed(db_session, country_directory=fake_countries)

    assert _count(db_session) == 0


@pytest.mark.parametrize("countries", [{}, {uuid4(): "COL", uuid4(): "COL"}])
def test_col_missing_or_ambiguous_writes_nothing(db_session, fake_countries, countries) -> None:
    fake_countries.countries = countries

    with pytest.raises(CountryNotFoundError):
        load_seed(db_session, country_directory=fake_countries)

    assert _count(db_session) == 0


def test_rules_of_another_country_are_reported_and_kept(db_session, test_engine) -> None:
    legacy_country = uuid4()
    load_seed(db_session, country_id=legacy_country)

    stats = load_seed(db_session, country_id=COLOMBIA_ID)

    assert stats.created == 8
    assert len(stats.warnings) == 8
    with test_engine.connect() as connection:
        kept = connection.execute(
            text("SELECT count(*) FROM identification_type_rules WHERE country_id = :id AND is_active"),
            {"id": legacy_country},
        ).scalar_one()
    assert kept == 8


def test_cli_explicit_parameter_does_not_request_token(monkeypatch, test_database_url, clean_database) -> None:
    monkeypatch.setenv("DATABASE_URL", test_database_url)
    monkeypatch.setenv("PARTY_IDENTITY_SEED_COUNTRY_ID", str(uuid4()))

    def forbidden(*args, **kwargs):
        raise AssertionError("El modo explícito no debe pedir token ni consultar Geography.")

    monkeypatch.setattr(seed_main, "build_geography_directory", forbidden)

    assert seed_main.main(["load", "--country-id", str(COLOMBIA_ID)]) == 0


def test_cli_environment_variable_selects_explicit_mode(monkeypatch, test_database_url, test_engine, clean_database) -> None:
    monkeypatch.setenv("DATABASE_URL", test_database_url)
    monkeypatch.setenv("PARTY_IDENTITY_SEED_COUNTRY_ID", str(COLOMBIA_ID))
    monkeypatch.setattr(seed_main, "build_geography_directory", lambda settings: pytest.fail("no debe usarse"))

    assert seed_main.main(["load"]) == 0
    with test_engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM identification_type_rules")).scalar_one() == 8


def test_cli_rejects_malformed_country_id(monkeypatch, test_database_url) -> None:
    monkeypatch.setenv("DATABASE_URL", test_database_url)

    with pytest.raises(SystemExit):
        seed_main.main(["load", "--country-id", "no-es-uuid"])


def test_cli_geography_mode_without_credentials_fails_without_writing(monkeypatch, test_database_url, test_engine, clean_database) -> None:
    monkeypatch.setenv("DATABASE_URL", test_database_url)
    for name in ("PARTY_IDENTITY_SEED_COUNTRY_ID", "KEYCLOAK_TOKEN_URL", "PARTY_IDENTITY_CLIENT_ID", "PARTY_IDENTITY_CLIENT_SECRET"):
        monkeypatch.setenv(name, "")

    assert seed_main.main(["load"]) == 1
    with test_engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM identification_type_rules")).scalar_one() == 0


# --------------------------------------------------------------------------
# load-business-sectors (T069): no cambia `load` ni usa Geography/Keycloak
# --------------------------------------------------------------------------

def test_cli_load_business_sectors_needs_no_geography_nor_token(monkeypatch, test_database_url, test_engine, clean_database) -> None:
    monkeypatch.setenv("DATABASE_URL", test_database_url)
    for name in ("PARTY_IDENTITY_SEED_COUNTRY_ID", "KEYCLOAK_TOKEN_URL", "PARTY_IDENTITY_CLIENT_ID", "PARTY_IDENTITY_CLIENT_SECRET"):
        monkeypatch.setenv(name, "")
    monkeypatch.setattr(seed_main, "build_geography_directory", lambda settings: pytest.fail("no debe usarse"))

    assert seed_main.main(["load-business-sectors"]) == 0
    assert seed_main.main(["load-business-sectors"]) == 0
    with test_engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM global_business_sectors")).scalar_one() == 919
        assert connection.execute(text("SELECT count(*) FROM identification_type_rules")).scalar_one() == 0


def test_cli_load_rules_does_not_touch_business_sectors(monkeypatch, test_database_url, test_engine, clean_database) -> None:
    monkeypatch.setenv("DATABASE_URL", test_database_url)

    assert seed_main.main(["load", "--country-id", str(COLOMBIA_ID)]) == 0
    with test_engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM identification_type_rules")).scalar_one() == 8
        assert connection.execute(text("SELECT count(*) FROM global_business_sectors")).scalar_one() == 0


def test_cli_load_business_sectors_fails_without_writing_on_bad_snapshot(monkeypatch, tmp_path, test_database_url, test_engine, clean_database) -> None:
    from party_identity_service.seed import business_sectors_loader

    (tmp_path / "ciiu_rev5_ac.csv").write_text("level,code,name,parent_code\nSECTION,A,x,\n", encoding="utf-8")
    (tmp_path / "SOURCE.md").write_text("- **SHA-256 del CSV (`ciiu_rev5_ac.csv`)**: `" + "0" * 64 + "`\n", encoding="utf-8")
    monkeypatch.setenv("DATABASE_URL", test_database_url)
    monkeypatch.setattr(business_sectors_loader.load_business_sectors, "__kwdefaults__",
                        {**business_sectors_loader.load_business_sectors.__kwdefaults__, "snapshot_dir": tmp_path})

    assert seed_main.main(["load-business-sectors"]) == 1
    with test_engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM global_business_sectors")).scalar_one() == 0
