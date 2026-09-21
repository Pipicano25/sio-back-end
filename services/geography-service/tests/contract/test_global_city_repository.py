"""Pruebas de persistencia para el repositorio de ciudades globales."""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from geography_service.application.exceptions import (
    GlobalCityConflictError,
    GlobalCityInvalidAdministrativeDivisionError,
    GlobalCityVersionConflictError,
)
from geography_service.domain.global_administrative_division import (
    GlobalAdministrativeDivision,
)
from geography_service.domain.global_country import (
    GlobalCountry,
)
from geography_service.infrastructure.global_administrative_division_repository import (
    SQLAlchemyGlobalAdministrativeDivisionRepository,
)
from geography_service.infrastructure.global_city_repository import (
    SQLAlchemyGlobalCityRepository,
)
from geography_service.infrastructure.global_country_repository import (
    SQLAlchemyGlobalCountryRepository,
)
from geography_service.infrastructure.models import (
    GlobalCityModel,
)


def create_country(
    db_session: Session,
    *,
    iso2_code: str = "CO",
    iso3_code: str = "COL",
    name: str = "Colombia",
) -> GlobalCountry:
    """Crea un país real en PostgreSQL para utilizarlo en una prueba.

    Args:
        db_session: Sesión SQLAlchemy conectada a PostgreSQL de pruebas.
        iso2_code: Código ISO alpha-2.
        iso3_code: Código ISO alpha-3.
        name: Nombre del país.

    Returns:
        País persistido.
    """
    repository = SQLAlchemyGlobalCountryRepository(
        db_session,
    )

    return repository.create(
        iso2_code=iso2_code,
        iso3_code=iso3_code,
        name=name,
        phone_prefix=None,
        status="ACTIVE",
        actor_id="country-creator",
    )


def create_division(
    db_session: Session,
    *,
    country_id,
    code: str = "ANT",
    name: str = "Antioquia",
    division_type: str = "DEPARTMENT",
) -> GlobalAdministrativeDivision:
    """Crea una división administrativa real para una prueba.

    Args:
        db_session: Sesión SQLAlchemy conectada a PostgreSQL de pruebas.
        country_id: Identificador del país propietario de la división.
        code: Código administrativo.
        name: Nombre de la división.
        division_type: Tipo de división administrativa.

    Returns:
        División administrativa persistida.
    """
    repository = (
        SQLAlchemyGlobalAdministrativeDivisionRepository(
            db_session,
        )
    )

    return repository.create(
        country_id=country_id,
        parent_division_id=None,
        code=code,
        name=name,
        division_type=division_type,
        status="ACTIVE",
        actor_id="division-creator",
    )


def test_create_persists_city_and_audit_fields(
    db_session: Session,
) -> None:
    """Comprueba creación, relación geográfica y auditoría de una ciudad.

    Args:
        db_session: Sesión SQLAlchemy conectada a PostgreSQL de pruebas.
    """
    country = create_country(
        db_session,
    )

    division = create_division(
        db_session,
        country_id=country.id,
    )

    repository = SQLAlchemyGlobalCityRepository(
        db_session,
    )

    actor_id = "keycloak-sub-user-001"

    city = repository.create(
        country_id=country.id,
        administrative_division_id=division.id,
        code="05001",
        name="Medellin",
        latitude=Decimal("6.244203"),
        longitude=Decimal("-75.581212"),
        status="ACTIVE",
        actor_id=actor_id,
    )

    stored = db_session.get(
        GlobalCityModel,
        city.id,
    )

    assert stored is not None

    assert stored.country_id == country.id
    assert stored.administrative_division_id == division.id

    assert stored.code == "05001"
    assert stored.name == "Medellin"

    assert stored.latitude == Decimal("6.244203")
    assert stored.longitude == Decimal("-75.581212")

    assert stored.status == "ACTIVE"
    assert stored.version == 1

    assert stored.created_by == actor_id
    assert stored.updated_by == actor_id

    assert stored.created_at is not None
    assert stored.updated_at is not None


def test_create_accepts_city_without_administrative_division(
    db_session: Session,
) -> None:
    """Comprueba que una ciudad pueda existir sin división administrativa.

    Args:
        db_session: Sesión SQLAlchemy conectada a PostgreSQL de pruebas.
    """
    country = create_country(
        db_session,
    )

    repository = SQLAlchemyGlobalCityRepository(
        db_session,
    )

    city = repository.create(
        country_id=country.id,
        administrative_division_id=None,
        code=None,
        name="Ciudad independiente",
        latitude=None,
        longitude=None,
        status="ACTIVE",
        actor_id="creator-user",
    )

    assert city.country_id == country.id
    assert city.administrative_division_id is None
    assert city.code is None
    assert city.latitude is None
    assert city.longitude is None


def test_get_by_id_returns_persisted_city(
    db_session: Session,
) -> None:
    """Comprueba la consulta de una ciudad persistida por UUID.

    Args:
        db_session: Sesión SQLAlchemy conectada a PostgreSQL de pruebas.
    """
    country = create_country(
        db_session,
    )

    repository = SQLAlchemyGlobalCityRepository(
        db_session,
    )

    created = repository.create(
        country_id=country.id,
        administrative_division_id=None,
        code="11001",
        name="Bogota",
        latitude=Decimal("4.711000"),
        longitude=Decimal("-74.072100"),
        status="ACTIVE",
        actor_id="creator-user",
    )

    result = repository.get_by_id(
        created.id,
    )

    assert result is not None
    assert result.id == created.id
    assert result.country_id == country.id
    assert result.name == "Bogota"


def test_get_by_id_returns_none_when_city_does_not_exist(
    db_session: Session,
) -> None:
    """Comprueba que consultar un UUID inexistente produzca None.

    Args:
        db_session: Sesión SQLAlchemy conectada a PostgreSQL de pruebas.
    """
    repository = SQLAlchemyGlobalCityRepository(
        db_session,
    )

    result = repository.get_by_id(
        uuid4(),
    )

    assert result is None


def test_list_all_returns_cities_ordered_by_name(
    db_session: Session,
) -> None:
    """Comprueba que las ciudades sean devueltas ordenadas por nombre.

    Args:
        db_session: Sesión SQLAlchemy conectada a PostgreSQL de pruebas.
    """
    country = create_country(
        db_session,
    )

    repository = SQLAlchemyGlobalCityRepository(
        db_session,
    )

    repository.create(
        country_id=country.id,
        administrative_division_id=None,
        code="05001",
        name="Medellin",
        latitude=None,
        longitude=None,
        status="ACTIVE",
        actor_id="creator-user",
    )

    repository.create(
        country_id=country.id,
        administrative_division_id=None,
        code="76001",
        name="Cali",
        latitude=None,
        longitude=None,
        status="ACTIVE",
        actor_id="creator-user",
    )

    repository.create(
        country_id=country.id,
        administrative_division_id=None,
        code="11001",
        name="Bogota",
        latitude=None,
        longitude=None,
        status="ACTIVE",
        actor_id="creator-user",
    )

    result = repository.list_all()

    names = [
        city.name
        for city in result
    ]

    assert names == [
        "Bogota",
        "Cali",
        "Medellin",
    ]


def test_create_rejects_nonexistent_country(
    db_session: Session,
) -> None:
    """Comprueba que no se cree una ciudad para un país inexistente.

    Args:
        db_session: Sesión SQLAlchemy conectada a PostgreSQL de pruebas.
    """
    repository = SQLAlchemyGlobalCityRepository(
        db_session,
    )

    with pytest.raises(
        GlobalCityConflictError,
        match="El país indicado no existe",
    ):
        repository.create(
            country_id=uuid4(),
            administrative_division_id=None,
            code="TEST",
            name="Ciudad inválida",
            latitude=None,
            longitude=None,
            status="ACTIVE",
            actor_id="creator-user",
        )


def test_create_accepts_division_from_same_country(
    db_session: Session,
) -> None:
    """Comprueba una relación válida entre ciudad y división administrativa.

    Args:
        db_session: Sesión SQLAlchemy conectada a PostgreSQL de pruebas.
    """
    country = create_country(
        db_session,
    )

    division = create_division(
        db_session,
        country_id=country.id,
    )

    repository = SQLAlchemyGlobalCityRepository(
        db_session,
    )

    city = repository.create(
        country_id=country.id,
        administrative_division_id=division.id,
        code="05001",
        name="Medellin",
        latitude=None,
        longitude=None,
        status="ACTIVE",
        actor_id="creator-user",
    )

    assert city.country_id == country.id
    assert city.administrative_division_id == division.id


def test_create_rejects_nonexistent_administrative_division(
    db_session: Session,
) -> None:
    """Comprueba que una división administrativa inexistente sea rechazada.

    Args:
        db_session: Sesión SQLAlchemy conectada a PostgreSQL de pruebas.
    """
    country = create_country(
        db_session,
    )

    repository = SQLAlchemyGlobalCityRepository(
        db_session,
    )

    with pytest.raises(
        GlobalCityInvalidAdministrativeDivisionError,
        match="no existe",
    ):
        repository.create(
            country_id=country.id,
            administrative_division_id=uuid4(),
            code="05001",
            name="Medellin",
            latitude=None,
            longitude=None,
            status="ACTIVE",
            actor_id="creator-user",
        )


def test_create_rejects_division_from_another_country(
    db_session: Session,
) -> None:
    """Comprueba que ciudad y división deban pertenecer al mismo país.

    Args:
        db_session: Sesión SQLAlchemy conectada a PostgreSQL de pruebas.
    """
    colombia = create_country(
        db_session,
        iso2_code="CO",
        iso3_code="COL",
        name="Colombia",
    )

    united_states = create_country(
        db_session,
        iso2_code="US",
        iso3_code="USA",
        name="Estados Unidos",
    )

    florida = create_division(
        db_session,
        country_id=united_states.id,
        code="FL",
        name="Florida",
        division_type="STATE",
    )

    repository = SQLAlchemyGlobalCityRepository(
        db_session,
    )

    with pytest.raises(
        GlobalCityInvalidAdministrativeDivisionError,
        match="mismo país",
    ):
        repository.create(
            country_id=colombia.id,
            administrative_division_id=florida.id,
            code="INVALID",
            name="Ciudad inválida",
            latitude=None,
            longitude=None,
            status="ACTIVE",
            actor_id="creator-user",
        )


def test_create_rejects_latitude_below_minimum(
    db_session: Session,
) -> None:
    """Comprueba el CHECK de PostgreSQL para latitudes menores a -90.

    Args:
        db_session: Sesión SQLAlchemy conectada a PostgreSQL de pruebas.
    """
    country = create_country(
        db_session,
    )

    repository = SQLAlchemyGlobalCityRepository(
        db_session,
    )

    with pytest.raises(
        GlobalCityConflictError,
    ):
        repository.create(
            country_id=country.id,
            administrative_division_id=None,
            code=None,
            name="Latitud inválida",
            latitude=Decimal("-90.000001"),
            longitude=Decimal("0"),
            status="ACTIVE",
            actor_id="creator-user",
        )


def test_create_rejects_latitude_above_maximum(
    db_session: Session,
) -> None:
    """Comprueba el CHECK de PostgreSQL para latitudes mayores a 90.

    Args:
        db_session: Sesión SQLAlchemy conectada a PostgreSQL de pruebas.
    """
    country = create_country(
        db_session,
    )

    repository = SQLAlchemyGlobalCityRepository(
        db_session,
    )

    with pytest.raises(
        GlobalCityConflictError,
    ):
        repository.create(
            country_id=country.id,
            administrative_division_id=None,
            code=None,
            name="Latitud inválida",
            latitude=Decimal("90.000001"),
            longitude=Decimal("0"),
            status="ACTIVE",
            actor_id="creator-user",
        )


def test_create_rejects_longitude_below_minimum(
    db_session: Session,
) -> None:
    """Comprueba el CHECK de PostgreSQL para longitudes menores a -180.

    Args:
        db_session: Sesión SQLAlchemy conectada a PostgreSQL de pruebas.
    """
    country = create_country(
        db_session,
    )

    repository = SQLAlchemyGlobalCityRepository(
        db_session,
    )

    with pytest.raises(
        GlobalCityConflictError,
    ):
        repository.create(
            country_id=country.id,
            administrative_division_id=None,
            code=None,
            name="Longitud inválida",
            latitude=Decimal("0"),
            longitude=Decimal("-180.000001"),
            status="ACTIVE",
            actor_id="creator-user",
        )


def test_create_rejects_longitude_above_maximum(
    db_session: Session,
) -> None:
    """Comprueba el CHECK de PostgreSQL para longitudes mayores a 180.

    Args:
        db_session: Sesión SQLAlchemy conectada a PostgreSQL de pruebas.
    """
    country = create_country(
        db_session,
    )

    repository = SQLAlchemyGlobalCityRepository(
        db_session,
    )

    with pytest.raises(
        GlobalCityConflictError,
    ):
        repository.create(
            country_id=country.id,
            administrative_division_id=None,
            code=None,
            name="Longitud inválida",
            latitude=Decimal("0"),
            longitude=Decimal("180.000001"),
            status="ACTIVE",
            actor_id="creator-user",
        )


def test_create_rejects_invalid_status(
    db_session: Session,
) -> None:
    """Comprueba que PostgreSQL rechace un estado fuera del dominio permitido.

    Args:
        db_session: Sesión SQLAlchemy conectada a PostgreSQL de pruebas.
    """
    country = create_country(
        db_session,
    )

    repository = SQLAlchemyGlobalCityRepository(
        db_session,
    )

    with pytest.raises(
        GlobalCityConflictError,
    ):
        repository.create(
            country_id=country.id,
            administrative_division_id=None,
            code=None,
            name="Ciudad inválida",
            latitude=None,
            longitude=None,
            status="INVALID",  # type: ignore[arg-type]
            actor_id="creator-user",
        )


def test_update_changes_city_and_increments_version(
    db_session: Session,
) -> None:
    """Comprueba actualización, auditoría y versión de una ciudad.

    Args:
        db_session: Sesión SQLAlchemy conectada a PostgreSQL de pruebas.
    """
    country = create_country(
        db_session,
    )

    division = create_division(
        db_session,
        country_id=country.id,
    )

    repository = SQLAlchemyGlobalCityRepository(
        db_session,
    )

    created = repository.create(
        country_id=country.id,
        administrative_division_id=division.id,
        code="05001",
        name="Medellin",
        latitude=Decimal("6.244203"),
        longitude=Decimal("-75.581212"),
        status="ACTIVE",
        actor_id="creator-user",
    )

    updated = repository.update(
        created.id,
        expected_version=1,
        country_id=country.id,
        administrative_division_id=division.id,
        code="05001",
        name="Medellin Distrito Especial",
        latitude=Decimal("6.244203"),
        longitude=Decimal("-75.581212"),
        status="ACTIVE",
        actor_id="editor-user",
    )

    assert updated is not None

    assert updated.id == created.id
    assert updated.name == "Medellin Distrito Especial"

    assert updated.version == 2

    assert updated.created_by == "creator-user"
    assert updated.updated_by == "editor-user"

    stored = db_session.get(
        GlobalCityModel,
        created.id,
    )

    assert stored is not None
    assert stored.version == 2
    assert stored.created_by == "creator-user"
    assert stored.updated_by == "editor-user"


def test_update_can_remove_administrative_division(
    db_session: Session,
) -> None:
    """Comprueba que una actualización permita eliminar la asociación divisional.

    Args:
        db_session: Sesión SQLAlchemy conectada a PostgreSQL de pruebas.
    """
    country = create_country(
        db_session,
    )

    division = create_division(
        db_session,
        country_id=country.id,
    )

    repository = SQLAlchemyGlobalCityRepository(
        db_session,
    )

    created = repository.create(
        country_id=country.id,
        administrative_division_id=division.id,
        code="05001",
        name="Medellin",
        latitude=None,
        longitude=None,
        status="ACTIVE",
        actor_id="creator-user",
    )

    updated = repository.update(
        created.id,
        expected_version=created.version,
        country_id=country.id,
        administrative_division_id=None,
        code=created.code,
        name=created.name,
        latitude=created.latitude,
        longitude=created.longitude,
        status=created.status,
        actor_id="editor-user",
    )

    assert updated is not None
    assert updated.administrative_division_id is None


def test_update_returns_none_when_city_does_not_exist(
    db_session: Session,
) -> None:
    """Comprueba que actualizar una ciudad inexistente produzca None.

    Args:
        db_session: Sesión SQLAlchemy conectada a PostgreSQL de pruebas.
    """
    country = create_country(
        db_session,
    )

    repository = SQLAlchemyGlobalCityRepository(
        db_session,
    )

    result = repository.update(
        uuid4(),
        expected_version=1,
        country_id=country.id,
        administrative_division_id=None,
        code="05001",
        name="Medellin",
        latitude=None,
        longitude=None,
        status="ACTIVE",
        actor_id="editor-user",
    )

    assert result is None


def test_update_rejects_stale_version(
    db_session: Session,
) -> None:
    """Comprueba que una versión obsoleta produzca conflicto.

    Args:
        db_session: Sesión SQLAlchemy conectada a PostgreSQL de pruebas.
    """
    country = create_country(
        db_session,
    )

    repository = SQLAlchemyGlobalCityRepository(
        db_session,
    )

    created = repository.create(
        country_id=country.id,
        administrative_division_id=None,
        code="05001",
        name="Medellin",
        latitude=None,
        longitude=None,
        status="ACTIVE",
        actor_id="creator-user",
    )

    first_update = repository.update(
        created.id,
        expected_version=1,
        country_id=country.id,
        administrative_division_id=None,
        code="05001",
        name="Medellin actualizada",
        latitude=None,
        longitude=None,
        status="ACTIVE",
        actor_id="editor-user-1",
    )

    assert first_update is not None
    assert first_update.version == 2

    with pytest.raises(
        GlobalCityVersionConflictError,
        match="El registro fue modificado",
    ):
        repository.update(
            created.id,
            expected_version=1,
            country_id=country.id,
            administrative_division_id=None,
            code="05001",
            name="Actualización obsoleta",
            latitude=None,
            longitude=None,
            status="ACTIVE",
            actor_id="editor-user-2",
        )


def test_update_rejects_division_from_another_country(
    db_session: Session,
) -> None:
    """Comprueba coherencia de país y división durante una actualización.

    Args:
        db_session: Sesión SQLAlchemy conectada a PostgreSQL de pruebas.
    """
    colombia = create_country(
        db_session,
        iso2_code="CO",
        iso3_code="COL",
        name="Colombia",
    )

    united_states = create_country(
        db_session,
        iso2_code="US",
        iso3_code="USA",
        name="Estados Unidos",
    )

    florida = create_division(
        db_session,
        country_id=united_states.id,
        code="FL",
        name="Florida",
        division_type="STATE",
    )

    repository = SQLAlchemyGlobalCityRepository(
        db_session,
    )

    city = repository.create(
        country_id=colombia.id,
        administrative_division_id=None,
        code="05001",
        name="Medellin",
        latitude=None,
        longitude=None,
        status="ACTIVE",
        actor_id="creator-user",
    )

    with pytest.raises(
        GlobalCityInvalidAdministrativeDivisionError,
        match="mismo país",
    ):
        repository.update(
            city.id,
            expected_version=city.version,
            country_id=colombia.id,
            administrative_division_id=florida.id,
            code=city.code,
            name=city.name,
            latitude=city.latitude,
            longitude=city.longitude,
            status=city.status,
            actor_id="editor-user",
        )


def test_delete_physically_removes_city(
    db_session: Session,
) -> None:
    """Comprueba que DELETE elimine físicamente una ciudad.

    Args:
        db_session: Sesión SQLAlchemy conectada a PostgreSQL de pruebas.
    """
    country = create_country(
        db_session,
    )

    repository = SQLAlchemyGlobalCityRepository(
        db_session,
    )

    city = repository.create(
        country_id=country.id,
        administrative_division_id=None,
        code="05001",
        name="Medellin",
        latitude=None,
        longitude=None,
        status="ACTIVE",
        actor_id="creator-user",
    )

    result = repository.delete(
        city.id,
    )

    assert result is True

    stored = db_session.get(
        GlobalCityModel,
        city.id,
    )

    assert stored is None


def test_delete_returns_false_when_city_does_not_exist(
    db_session: Session,
) -> None:
    """Comprueba la eliminación de una ciudad inexistente.

    Args:
        db_session: Sesión SQLAlchemy conectada a PostgreSQL de pruebas.
    """
    repository = SQLAlchemyGlobalCityRepository(
        db_session,
    )

    result = repository.delete(
        uuid4(),
    )

    assert result is False
