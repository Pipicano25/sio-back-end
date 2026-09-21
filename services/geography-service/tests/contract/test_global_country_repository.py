"""Pruebas de persistencia para el repositorio de países globales."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from geography_service.application.exceptions import (
    GlobalCountryConflictError,
    GlobalCountryVersionConflictError,
)
from geography_service.infrastructure.global_country_repository import (
    SQLAlchemyGlobalCountryRepository,
)
from geography_service.infrastructure.models import (
    GlobalCountryModel,
)


def test_create_persists_country_and_audit_fields(
    db_session: Session,
) -> None:
    """Comprueba que un país sea almacenado con su información de auditoría.

    Args:
        db_session: Sesión SQLAlchemy conectada a PostgreSQL de pruebas.
    """
    repository = SQLAlchemyGlobalCountryRepository(
        db_session,
    )

    actor_id = "keycloak-sub-user-001"

    country = repository.create(
        iso2_code="CO",
        iso3_code="COL",
        name="Colombia",
        phone_prefix="+57",
        status="ACTIVE",
        actor_id=actor_id,
    )

    stored = db_session.get(
        GlobalCountryModel,
        country.id,
    )

    assert stored is not None

    assert stored.iso2_code == "CO"
    assert stored.iso3_code == "COL"
    assert stored.name == "Colombia"
    assert stored.phone_prefix == "+57"
    assert stored.status == "ACTIVE"

    assert stored.version == 1

    assert stored.created_by == actor_id
    assert stored.updated_by == actor_id

    assert stored.created_at is not None
    assert stored.updated_at is not None


def test_get_by_id_returns_persisted_country(
    db_session: Session,
) -> None:
    """Comprueba que un país persistido pueda recuperarse por UUID.

    Args:
        db_session: Sesión SQLAlchemy conectada a PostgreSQL de pruebas.
    """
    repository = SQLAlchemyGlobalCountryRepository(
        db_session,
    )

    created = repository.create(
        iso2_code="CO",
        iso3_code="COL",
        name="Colombia",
        phone_prefix="+57",
        status="ACTIVE",
        actor_id="creator-user",
    )

    result = repository.get_by_id(
        created.id,
    )

    assert result is not None
    assert result.id == created.id
    assert result.iso2_code == "CO"
    assert result.iso3_code == "COL"
    assert result.name == "Colombia"


def test_get_by_id_returns_none_when_country_does_not_exist(
    db_session: Session,
) -> None:
    """Comprueba que consultar un UUID inexistente produzca None.

    Args:
        db_session: Sesión SQLAlchemy conectada a PostgreSQL de pruebas.
    """
    repository = SQLAlchemyGlobalCountryRepository(
        db_session,
    )

    result = repository.get_by_id(
        uuid4(),
    )

    assert result is None


def test_list_all_returns_countries_ordered_by_name(
    db_session: Session,
) -> None:
    """Comprueba que los países se devuelvan ordenados por nombre.

    Args:
        db_session: Sesión SQLAlchemy conectada a PostgreSQL de pruebas.
    """
    repository = SQLAlchemyGlobalCountryRepository(
        db_session,
    )

    repository.create(
        iso2_code="MX",
        iso3_code="MEX",
        name="México",
        phone_prefix="+52",
        status="ACTIVE",
        actor_id="creator-user",
    )

    repository.create(
        iso2_code="CO",
        iso3_code="COL",
        name="Colombia",
        phone_prefix="+57",
        status="ACTIVE",
        actor_id="creator-user",
    )

    repository.create(
        iso2_code="AR",
        iso3_code="ARG",
        name="Argentina",
        phone_prefix="+54",
        status="ACTIVE",
        actor_id="creator-user",
    )

    result = repository.list_all()

    names = [
        country.name
        for country in result
    ]

    assert names == [
        "Argentina",
        "Colombia",
        "México",
    ]


def test_create_rejects_duplicate_iso2_code(
    db_session: Session,
) -> None:
    """Comprueba la restricción única del código ISO alpha-2.

    Args:
        db_session: Sesión SQLAlchemy conectada a PostgreSQL de pruebas.
    """
    repository = SQLAlchemyGlobalCountryRepository(
        db_session,
    )

    repository.create(
        iso2_code="CO",
        iso3_code="COL",
        name="Colombia",
        phone_prefix="+57",
        status="ACTIVE",
        actor_id="creator-user",
    )

    with pytest.raises(
        GlobalCountryConflictError,
    ):
        repository.create(
            iso2_code="CO",
            iso3_code="XXX",
            name="País duplicado",
            phone_prefix=None,
            status="ACTIVE",
            actor_id="creator-user",
        )


def test_create_rejects_duplicate_iso3_code(
    db_session: Session,
) -> None:
    """Comprueba la restricción única del código ISO alpha-3.

    Args:
        db_session: Sesión SQLAlchemy conectada a PostgreSQL de pruebas.
    """
    repository = SQLAlchemyGlobalCountryRepository(
        db_session,
    )

    repository.create(
        iso2_code="CO",
        iso3_code="COL",
        name="Colombia",
        phone_prefix="+57",
        status="ACTIVE",
        actor_id="creator-user",
    )

    with pytest.raises(
        GlobalCountryConflictError,
    ):
        repository.create(
            iso2_code="XX",
            iso3_code="COL",
            name="País duplicado",
            phone_prefix=None,
            status="ACTIVE",
            actor_id="creator-user",
        )


def test_update_changes_country_and_increments_version(
    db_session: Session,
) -> None:
    """Comprueba actualización, auditoría y concurrencia optimista.

    Args:
        db_session: Sesión SQLAlchemy conectada a PostgreSQL de pruebas.
    """
    repository = SQLAlchemyGlobalCountryRepository(
        db_session,
    )

    created = repository.create(
        iso2_code="CO",
        iso3_code="COL",
        name="Colombia",
        phone_prefix="+57",
        status="ACTIVE",
        actor_id="creator-user",
    )

    updated = repository.update(
        created.id,
        expected_version=1,
        iso2_code="CO",
        iso3_code="COL",
        name="República de Colombia",
        phone_prefix="+57",
        status="ACTIVE",
        actor_id="editor-user",
    )

    assert updated is not None

    assert updated.id == created.id
    assert updated.name == "República de Colombia"

    assert updated.version == 2

    assert updated.created_by == "creator-user"
    assert updated.updated_by == "editor-user"

    stored = db_session.get(
        GlobalCountryModel,
        created.id,
    )

    assert stored is not None
    assert stored.version == 2
    assert stored.created_by == "creator-user"
    assert stored.updated_by == "editor-user"


def test_update_returns_none_when_country_does_not_exist(
    db_session: Session,
) -> None:
    """Comprueba que actualizar un país inexistente produzca None.

    Args:
        db_session: Sesión SQLAlchemy conectada a PostgreSQL de pruebas.
    """
    repository = SQLAlchemyGlobalCountryRepository(
        db_session,
    )

    result = repository.update(
        uuid4(),
        expected_version=1,
        iso2_code="CO",
        iso3_code="COL",
        name="Colombia",
        phone_prefix="+57",
        status="ACTIVE",
        actor_id="editor-user",
    )

    assert result is None


def test_update_rejects_stale_version(
    db_session: Session,
) -> None:
    """Comprueba que una versión antigua produzca conflicto.

    Args:
        db_session: Sesión SQLAlchemy conectada a PostgreSQL de pruebas.
    """
    repository = SQLAlchemyGlobalCountryRepository(
        db_session,
    )

    created = repository.create(
        iso2_code="CO",
        iso3_code="COL",
        name="Colombia",
        phone_prefix="+57",
        status="ACTIVE",
        actor_id="creator-user",
    )

    first_update = repository.update(
        created.id,
        expected_version=1,
        iso2_code="CO",
        iso3_code="COL",
        name="República de Colombia",
        phone_prefix="+57",
        status="ACTIVE",
        actor_id="editor-user-1",
    )

    assert first_update is not None
    assert first_update.version == 2

    with pytest.raises(
        GlobalCountryVersionConflictError,
        match="El registro fue modificado",
    ):
        repository.update(
            created.id,
            expected_version=1,
            iso2_code="CO",
            iso3_code="COL",
            name="Colombia modificada",
            phone_prefix="+57",
            status="ACTIVE",
            actor_id="editor-user-2",
        )


def test_update_rejects_duplicate_iso_code(
    db_session: Session,
) -> None:
    """Comprueba que una actualización no pueda duplicar códigos ISO.

    Args:
        db_session: Sesión SQLAlchemy conectada a PostgreSQL de pruebas.
    """
    repository = SQLAlchemyGlobalCountryRepository(
        db_session,
    )

    colombia = repository.create(
        iso2_code="CO",
        iso3_code="COL",
        name="Colombia",
        phone_prefix="+57",
        status="ACTIVE",
        actor_id="creator-user",
    )

    mexico = repository.create(
        iso2_code="MX",
        iso3_code="MEX",
        name="México",
        phone_prefix="+52",
        status="ACTIVE",
        actor_id="creator-user",
    )

    with pytest.raises(
        GlobalCountryConflictError,
    ):
        repository.update(
            mexico.id,
            expected_version=mexico.version,
            iso2_code=colombia.iso2_code,
            iso3_code=mexico.iso3_code,
            name=mexico.name,
            phone_prefix=mexico.phone_prefix,
            status=mexico.status,
            actor_id="editor-user",
        )


def test_delete_physically_removes_country(
    db_session: Session,
) -> None:
    """Comprueba que DELETE elimine físicamente el registro.

    Args:
        db_session: Sesión SQLAlchemy conectada a PostgreSQL de pruebas.
    """
    repository = SQLAlchemyGlobalCountryRepository(
        db_session,
    )

    created = repository.create(
        iso2_code="CO",
        iso3_code="COL",
        name="Colombia",
        phone_prefix="+57",
        status="ACTIVE",
        actor_id="creator-user",
    )

    result = repository.delete(
        created.id,
    )

    assert result is True

    stored = db_session.get(
        GlobalCountryModel,
        created.id,
    )

    assert stored is None


def test_delete_returns_false_when_country_does_not_exist(
    db_session: Session,
) -> None:
    """Comprueba la eliminación de un UUID inexistente.

    Args:
        db_session: Sesión SQLAlchemy conectada a PostgreSQL de pruebas.
    """
    repository = SQLAlchemyGlobalCountryRepository(
        db_session,
    )

    result = repository.delete(
        uuid4(),
    )

    assert result is False
