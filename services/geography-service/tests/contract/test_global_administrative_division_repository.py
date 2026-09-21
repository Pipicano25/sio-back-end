"""Pruebas de persistencia para divisiones administrativas globales."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session

from geography_service.application.exceptions import (
    GlobalAdministrativeDivisionConflictError,
    GlobalAdministrativeDivisionInvalidParentError,
    GlobalAdministrativeDivisionVersionConflictError,
)
from geography_service.domain.global_country import (
    GlobalCountry,
)
from geography_service.infrastructure.global_administrative_division_repository import (
    SQLAlchemyGlobalAdministrativeDivisionRepository,
)
from geography_service.infrastructure.global_country_repository import (
    SQLAlchemyGlobalCountryRepository,
)
from geography_service.infrastructure.models import (
    GlobalAdministrativeDivisionModel,
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


def test_create_persists_division_and_audit_fields(
    db_session: Session,
) -> None:
    """Comprueba creación y auditoría de una división administrativa.

    Args:
        db_session: Sesión SQLAlchemy conectada a PostgreSQL de pruebas.
    """
    country = create_country(
        db_session,
    )

    repository = (
        SQLAlchemyGlobalAdministrativeDivisionRepository(
            db_session,
        )
    )

    actor_id = "keycloak-sub-user-001"

    division = repository.create(
        country_id=country.id,
        parent_division_id=None,
        code="ANT",
        name="Antioquia",
        division_type="DEPARTMENT",
        status="ACTIVE",
        actor_id=actor_id,
    )

    stored = db_session.get(
        GlobalAdministrativeDivisionModel,
        division.id,
    )

    assert stored is not None

    assert stored.country_id == country.id
    assert stored.parent_division_id is None

    assert stored.code == "ANT"
    assert stored.name == "Antioquia"
    assert stored.division_type == "DEPARTMENT"
    assert stored.status == "ACTIVE"

    assert stored.version == 1

    assert stored.created_by == actor_id
    assert stored.updated_by == actor_id

    assert stored.created_at is not None
    assert stored.updated_at is not None


def test_get_by_id_returns_persisted_division(
    db_session: Session,
) -> None:
    """Comprueba la consulta de una división persistida por UUID.

    Args:
        db_session: Sesión SQLAlchemy conectada a PostgreSQL de pruebas.
    """
    country = create_country(
        db_session,
    )

    repository = (
        SQLAlchemyGlobalAdministrativeDivisionRepository(
            db_session,
        )
    )

    created = repository.create(
        country_id=country.id,
        parent_division_id=None,
        code="ANT",
        name="Antioquia",
        division_type="DEPARTMENT",
        status="ACTIVE",
        actor_id="creator-user",
    )

    result = repository.get_by_id(
        created.id,
    )

    assert result is not None
    assert result.id == created.id
    assert result.country_id == country.id
    assert result.name == "Antioquia"


def test_get_by_id_returns_none_when_division_does_not_exist(
    db_session: Session,
) -> None:
    """Comprueba que un UUID inexistente produzca None.

    Args:
        db_session: Sesión SQLAlchemy conectada a PostgreSQL de pruebas.
    """
    repository = (
        SQLAlchemyGlobalAdministrativeDivisionRepository(
            db_session,
        )
    )

    result = repository.get_by_id(
        uuid4(),
    )

    assert result is None


def test_list_all_returns_divisions_ordered_by_name(
    db_session: Session,
) -> None:
    """Comprueba que las divisiones se devuelvan ordenadas por nombre.

    Args:
        db_session: Sesión SQLAlchemy conectada a PostgreSQL de pruebas.
    """
    country = create_country(
        db_session,
    )

    repository = (
        SQLAlchemyGlobalAdministrativeDivisionRepository(
            db_session,
        )
    )

    repository.create(
        country_id=country.id,
        parent_division_id=None,
        code="CUN",
        name="Cundinamarca",
        division_type="DEPARTMENT",
        status="ACTIVE",
        actor_id="creator-user",
    )

    repository.create(
        country_id=country.id,
        parent_division_id=None,
        code="ANT",
        name="Antioquia",
        division_type="DEPARTMENT",
        status="ACTIVE",
        actor_id="creator-user",
    )

    result = repository.list_all()

    names = [
        division.name
        for division in result
    ]

    assert names == [
        "Antioquia",
        "Cundinamarca",
    ]


def test_create_rejects_nonexistent_country(
    db_session: Session,
) -> None:
    """Comprueba que no se pueda crear una división con país inexistente.

    Args:
        db_session: Sesión SQLAlchemy conectada a PostgreSQL de pruebas.
    """
    repository = (
        SQLAlchemyGlobalAdministrativeDivisionRepository(
            db_session,
        )
    )

    with pytest.raises(
        GlobalAdministrativeDivisionConflictError,
        match="El país indicado no existe",
    ):
        repository.create(
            country_id=uuid4(),
            parent_division_id=None,
            code="TEST",
            name="División inválida",
            division_type="OTHER",
            status="ACTIVE",
            actor_id="creator-user",
        )


def test_create_accepts_parent_from_same_country(
    db_session: Session,
) -> None:
    """Comprueba una relación parent válida dentro del mismo país.

    Args:
        db_session: Sesión SQLAlchemy conectada a PostgreSQL de pruebas.
    """
    country = create_country(
        db_session,
    )

    repository = (
        SQLAlchemyGlobalAdministrativeDivisionRepository(
            db_session,
        )
    )

    parent = repository.create(
        country_id=country.id,
        parent_division_id=None,
        code="REG-01",
        name="Región Principal",
        division_type="REGION",
        status="ACTIVE",
        actor_id="creator-user",
    )

    child = repository.create(
        country_id=country.id,
        parent_division_id=parent.id,
        code="DIST-01",
        name="Distrito Interno",
        division_type="DISTRICT",
        status="ACTIVE",
        actor_id="creator-user",
    )

    assert child.country_id == country.id
    assert child.parent_division_id == parent.id


def test_create_rejects_nonexistent_parent(
    db_session: Session,
) -> None:
    """Comprueba que una división superior inexistente sea rechazada.

    Args:
        db_session: Sesión SQLAlchemy conectada a PostgreSQL de pruebas.
    """
    country = create_country(
        db_session,
    )

    repository = (
        SQLAlchemyGlobalAdministrativeDivisionRepository(
            db_session,
        )
    )

    with pytest.raises(
        GlobalAdministrativeDivisionInvalidParentError,
        match="superior indicada no existe",
    ):
        repository.create(
            country_id=country.id,
            parent_division_id=uuid4(),
            code="TEST",
            name="División inválida",
            division_type="OTHER",
            status="ACTIVE",
            actor_id="creator-user",
        )


def test_create_rejects_parent_from_another_country(
    db_session: Session,
) -> None:
    """Comprueba que parent y división deban pertenecer al mismo país.

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

    repository = (
        SQLAlchemyGlobalAdministrativeDivisionRepository(
            db_session,
        )
    )

    florida = repository.create(
        country_id=united_states.id,
        parent_division_id=None,
        code="FL",
        name="Florida",
        division_type="STATE",
        status="ACTIVE",
        actor_id="creator-user",
    )

    with pytest.raises(
        GlobalAdministrativeDivisionInvalidParentError,
        match="mismo país",
    ):
        repository.create(
            country_id=colombia.id,
            parent_division_id=florida.id,
            code="INVALID",
            name="División inválida",
            division_type="OTHER",
            status="ACTIVE",
            actor_id="creator-user",
        )


def test_update_changes_division_and_increments_version(
    db_session: Session,
) -> None:
    """Comprueba actualización, auditoría y versión de una división.

    Args:
        db_session: Sesión SQLAlchemy conectada a PostgreSQL de pruebas.
    """
    country = create_country(
        db_session,
    )

    repository = (
        SQLAlchemyGlobalAdministrativeDivisionRepository(
            db_session,
        )
    )

    created = repository.create(
        country_id=country.id,
        parent_division_id=None,
        code="ANT",
        name="Antioquia",
        division_type="DEPARTMENT",
        status="ACTIVE",
        actor_id="creator-user",
    )

    updated = repository.update(
        created.id,
        expected_version=1,
        country_id=country.id,
        parent_division_id=None,
        code="ANT",
        name="Departamento de Antioquia",
        division_type="DEPARTMENT",
        status="ACTIVE",
        actor_id="editor-user",
    )

    assert updated is not None

    assert updated.id == created.id
    assert updated.name == "Departamento de Antioquia"

    assert updated.version == 2

    assert updated.created_by == "creator-user"
    assert updated.updated_by == "editor-user"

    stored = db_session.get(
        GlobalAdministrativeDivisionModel,
        created.id,
    )

    assert stored is not None
    assert stored.version == 2
    assert stored.created_by == "creator-user"
    assert stored.updated_by == "editor-user"


def test_update_returns_none_when_division_does_not_exist(
    db_session: Session,
) -> None:
    """Comprueba la actualización de una división inexistente.

    Args:
        db_session: Sesión SQLAlchemy conectada a PostgreSQL de pruebas.
    """
    country = create_country(
        db_session,
    )

    repository = (
        SQLAlchemyGlobalAdministrativeDivisionRepository(
            db_session,
        )
    )

    result = repository.update(
        uuid4(),
        expected_version=1,
        country_id=country.id,
        parent_division_id=None,
        code="ANT",
        name="Antioquia",
        division_type="DEPARTMENT",
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

    repository = (
        SQLAlchemyGlobalAdministrativeDivisionRepository(
            db_session,
        )
    )

    created = repository.create(
        country_id=country.id,
        parent_division_id=None,
        code="ANT",
        name="Antioquia",
        division_type="DEPARTMENT",
        status="ACTIVE",
        actor_id="creator-user",
    )

    first_update = repository.update(
        created.id,
        expected_version=1,
        country_id=country.id,
        parent_division_id=None,
        code="ANT",
        name="Antioquia actualizada",
        division_type="DEPARTMENT",
        status="ACTIVE",
        actor_id="editor-user-1",
    )

    assert first_update is not None
    assert first_update.version == 2

    with pytest.raises(
        GlobalAdministrativeDivisionVersionConflictError,
        match="El registro fue modificado",
    ):
        repository.update(
            created.id,
            expected_version=1,
            country_id=country.id,
            parent_division_id=None,
            code="ANT",
            name="Actualización obsoleta",
            division_type="DEPARTMENT",
            status="ACTIVE",
            actor_id="editor-user-2",
        )


def test_update_rejects_itself_as_parent(
    db_session: Session,
) -> None:
    """Comprueba que una división no pueda ser su propia superior.

    Args:
        db_session: Sesión SQLAlchemy conectada a PostgreSQL de pruebas.
    """
    country = create_country(
        db_session,
    )

    repository = (
        SQLAlchemyGlobalAdministrativeDivisionRepository(
            db_session,
        )
    )

    division = repository.create(
        country_id=country.id,
        parent_division_id=None,
        code="ANT",
        name="Antioquia",
        division_type="DEPARTMENT",
        status="ACTIVE",
        actor_id="creator-user",
    )

    with pytest.raises(
        GlobalAdministrativeDivisionInvalidParentError,
        match="no puede ser su propia",
    ):
        repository.update(
            division.id,
            expected_version=division.version,
            country_id=country.id,
            parent_division_id=division.id,
            code=division.code,
            name=division.name,
            division_type=division.division_type,
            status=division.status,
            actor_id="editor-user",
        )


def test_update_rejects_parent_from_another_country(
    db_session: Session,
) -> None:
    """Comprueba la coherencia entre país y parent durante actualización.

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

    repository = (
        SQLAlchemyGlobalAdministrativeDivisionRepository(
            db_session,
        )
    )

    antioquia = repository.create(
        country_id=colombia.id,
        parent_division_id=None,
        code="ANT",
        name="Antioquia",
        division_type="DEPARTMENT",
        status="ACTIVE",
        actor_id="creator-user",
    )

    florida = repository.create(
        country_id=united_states.id,
        parent_division_id=None,
        code="FL",
        name="Florida",
        division_type="STATE",
        status="ACTIVE",
        actor_id="creator-user",
    )

    with pytest.raises(
        GlobalAdministrativeDivisionInvalidParentError,
        match="mismo país",
    ):
        repository.update(
            antioquia.id,
            expected_version=antioquia.version,
            country_id=colombia.id,
            parent_division_id=florida.id,
            code=antioquia.code,
            name=antioquia.name,
            division_type=antioquia.division_type,
            status=antioquia.status,
            actor_id="editor-user",
        )


def test_delete_physically_removes_division(
    db_session: Session,
) -> None:
    """Comprueba que DELETE elimine físicamente una división.

    Args:
        db_session: Sesión SQLAlchemy conectada a PostgreSQL de pruebas.
    """
    country = create_country(
        db_session,
    )

    repository = (
        SQLAlchemyGlobalAdministrativeDivisionRepository(
            db_session,
        )
    )

    division = repository.create(
        country_id=country.id,
        parent_division_id=None,
        code="ANT",
        name="Antioquia",
        division_type="DEPARTMENT",
        status="ACTIVE",
        actor_id="creator-user",
    )

    result = repository.delete(
        division.id,
    )

    assert result is True

    stored = db_session.get(
        GlobalAdministrativeDivisionModel,
        division.id,
    )

    assert stored is None


def test_delete_returns_false_when_division_does_not_exist(
    db_session: Session,
) -> None:
    """Comprueba la eliminación de una división inexistente.

    Args:
        db_session: Sesión SQLAlchemy conectada a PostgreSQL de pruebas.
    """
    repository = (
        SQLAlchemyGlobalAdministrativeDivisionRepository(
            db_session,
        )
    )

    result = repository.delete(
        uuid4(),
    )

    assert result is False


def test_delete_rejects_parent_with_child_division(
    db_session: Session,
) -> None:
    """Comprueba que una división con hijos no pueda eliminarse.

    PostgreSQL debe aplicar la foreign key con ON DELETE RESTRICT y el
    repositorio debe transformar el error de integridad en una excepción
    propia de la aplicación.

    Args:
        db_session: Sesión SQLAlchemy conectada a PostgreSQL de pruebas.
    """
    country = create_country(
        db_session,
    )

    repository = (
        SQLAlchemyGlobalAdministrativeDivisionRepository(
            db_session,
        )
    )

    parent = repository.create(
        country_id=country.id,
        parent_division_id=None,
        code="REG-01",
        name="Región Principal",
        division_type="REGION",
        status="ACTIVE",
        actor_id="creator-user",
    )

    repository.create(
        country_id=country.id,
        parent_division_id=parent.id,
        code="DIST-01",
        name="Distrito Interno",
        division_type="DISTRICT",
        status="ACTIVE",
        actor_id="creator-user",
    )

    with pytest.raises(
        GlobalAdministrativeDivisionConflictError,
        match="existen registros relacionados",
    ):
        repository.delete(
            parent.id,
        )
