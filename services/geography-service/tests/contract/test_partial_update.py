"""`PUT` parcial y versión opcional (constitución 4.0.0: Principio VII, D9 y D28).

- Un campo no enviado conserva su valor; la coherencia país–división se valida sobre el resultado.
- `version` es opcional: si llega y no coincide, conflicto; si no llega, gana la última escritura.
- El esquema rechaza un cuerpo vacío, solo con `version`, con `null` en un campo obligatorio o con
  un campo desconocido.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from geography_service.api.schemas.global_city import GlobalCityUpdate
from geography_service.api.schemas.global_country import GlobalCountryUpdate
from geography_service.application.exceptions import GlobalCityVersionConflictError
from geography_service.infrastructure.global_administrative_division_repository import (
    SQLAlchemyGlobalAdministrativeDivisionRepository,
)
from geography_service.infrastructure.global_city_repository import SQLAlchemyGlobalCityRepository
from geography_service.infrastructure.global_country_repository import SQLAlchemyGlobalCountryRepository


def create_country(db_session: Session):
    return SQLAlchemyGlobalCountryRepository(db_session).create(
        iso2_code="CO", iso3_code="COL", name="Colombia", phone_prefix=None, status="ACTIVE", actor_id="creator"
    )


def create_division(db_session: Session, *, country_id):
    return SQLAlchemyGlobalAdministrativeDivisionRepository(db_session).create(
        country_id=country_id,
        parent_division_id=None,
        code="ANT",
        name="Antioquia",
        division_type="DEPARTMENT",
        status="ACTIVE",
        actor_id="creator",
    )


def _city(db_session: Session):
    country = create_country(db_session)
    division = create_division(db_session, country_id=country.id)
    repository = SQLAlchemyGlobalCityRepository(db_session)
    city = repository.create(
        country_id=country.id,
        administrative_division_id=division.id,
        code="05001",
        name="Medellin",
        latitude=Decimal("6.244203"),
        longitude=Decimal("-75.581212"),
        status="ACTIVE",
        actor_id="creator-user",
    )
    return repository, city


def test_city_update_with_one_field_keeps_the_rest(db_session: Session) -> None:
    repository, city = _city(db_session)

    updated = repository.update(city.id, expected_version=None, name="Medellin Distrito", actor_id="editor")

    assert updated.name == "Medellin Distrito"
    assert updated.code == "05001"
    assert updated.administrative_division_id == city.administrative_division_id
    assert updated.latitude == city.latitude
    assert updated.version == city.version + 1


def test_city_update_with_stale_version_is_conflict(db_session: Session) -> None:
    repository, city = _city(db_session)
    repository.update(city.id, expected_version=None, name="Primero", actor_id="editor")

    with pytest.raises(GlobalCityVersionConflictError):
        repository.update(city.id, expected_version=city.version, name="Segundo", actor_id="editor")


def test_city_update_can_clear_an_optional_field(db_session: Session) -> None:
    repository, city = _city(db_session)

    updated = repository.update(city.id, expected_version=None, administrative_division_id=None, actor_id="editor")

    assert updated.administrative_division_id is None
    assert updated.name == "Medellin"


def test_country_update_changes_only_the_prefix(db_session: Session) -> None:
    country = create_country(db_session)
    repository = SQLAlchemyGlobalCountryRepository(db_session)

    updated = repository.update(country.id, expected_version=None, phone_prefix="+57", actor_id="editor")

    assert updated.phone_prefix == "+57"
    assert (updated.iso2_code, updated.iso3_code, updated.name) == ("CO", "COL", "Colombia")


@pytest.mark.parametrize("body", [{}, {"version": 1}, {"name": None}, {"nombre": "X"}])
def test_city_schema_rejects_bodies_without_valid_changes(body) -> None:
    with pytest.raises(ValidationError):
        GlobalCityUpdate.model_validate(body)


def test_schemas_keep_only_sent_fields() -> None:
    assert GlobalCityUpdate.model_validate({"code": None}).changes() == {"code": None}
    assert GlobalCountryUpdate.model_validate({"name": "Colombia", "version": 3}).changes() == {"name": "Colombia"}
