"""Pruebas unitarias para los casos de uso de países globales."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from geography_service.application.exceptions import (
    GlobalCountryConflictError,
    GlobalCountryNotFoundError,
    GlobalCountryVersionConflictError,
)
from geography_service.application.global_country_service import (
    GlobalCountryService,
)
from geography_service.domain.global_country import (
    GlobalCountry,
    GlobalCountryStatus,
)


class FakeGlobalCountryRepository:
    """Repositorio falso utilizado para probar GlobalCountryService.

    Este repositorio mantiene la información únicamente en memoria y permite
    comprobar los casos de uso de la capa de aplicación sin depender de
    SQLAlchemy ni PostgreSQL.

    Attributes:
        countries: Registros disponibles en el repositorio falso.
        last_create_actor_id: Actor recibido en la última creación.
        last_update_actor_id: Actor recibido en la última actualización.
        last_expected_version: Versión recibida en la última actualización.
    """

    def __init__(
        self,
        countries: list[GlobalCountry] | None = None,
    ) -> None:
        """Inicializa el repositorio falso.

        Args:
            countries: Países que estarán disponibles inicialmente.
        """
        self.countries = {
            country.id: country
            for country in (countries or [])
        }

        self.last_create_actor_id: str | None = None
        self.last_update_actor_id: str | None = None
        self.last_expected_version: int | None = None

        self.raise_create_conflict = False
        self.raise_update_conflict = False
        self.raise_version_conflict = False

    def list_all(self) -> list[GlobalCountry]:
        """Obtiene todos los países disponibles.

        Returns:
            Lista de países almacenados en memoria.
        """
        return list(
            self.countries.values(),
        )

    def get_by_id(
        self,
        country_id: UUID,
    ) -> GlobalCountry | None:
        """Obtiene un país por identificador.

        Args:
            country_id: Identificador del país.

        Returns:
            País encontrado o None si no existe.
        """
        return self.countries.get(
            country_id,
        )

    def create(
        self,
        *,
        iso2_code: str,
        iso3_code: str,
        name: str,
        phone_prefix: str | None,
        status: GlobalCountryStatus,
        actor_id: str,
    ) -> GlobalCountry:
        """Crea un país dentro del repositorio falso.

        Args:
            iso2_code: Código ISO alpha-2.
            iso3_code: Código ISO alpha-3.
            name: Nombre del país.
            phone_prefix: Prefijo telefónico internacional.
            status: Estado funcional.
            actor_id: Usuario autenticado que crea el registro.

        Returns:
            País creado.

        Raises:
            GlobalCountryConflictError: Si la prueba configuró un conflicto.
        """
        if self.raise_create_conflict:
            raise GlobalCountryConflictError(
                "Conflicto simulado durante la creación."
            )

        self.last_create_actor_id = actor_id

        now = datetime.now(
            UTC,
        )

        country = GlobalCountry(
            id=uuid4(),
            iso2_code=iso2_code,
            iso3_code=iso3_code,
            name=name,
            phone_prefix=phone_prefix,
            status=status,
            version=1,
            created_by=actor_id,
            updated_by=actor_id,
            created_at=now,
            updated_at=now,
        )

        self.countries[country.id] = country

        return country

    def update(
        self,
        country_id: UUID,
        *,
        expected_version: int,
        iso2_code: str,
        iso3_code: str,
        name: str,
        phone_prefix: str | None,
        status: GlobalCountryStatus,
        actor_id: str,
    ) -> GlobalCountry | None:
        """Actualiza un país dentro del repositorio falso.

        Args:
            country_id: Identificador del país.
            expected_version: Versión conocida por el cliente.
            iso2_code: Código ISO alpha-2.
            iso3_code: Código ISO alpha-3.
            name: Nombre del país.
            phone_prefix: Prefijo telefónico internacional.
            status: Estado funcional.
            actor_id: Usuario autenticado que modifica el registro.

        Returns:
            País actualizado o None cuando no existe.

        Raises:
            GlobalCountryConflictError: Si la prueba configura un conflicto.
            GlobalCountryVersionConflictError: Si la prueba configura un
                conflicto de concurrencia.
        """
        self.last_update_actor_id = actor_id
        self.last_expected_version = expected_version

        if self.raise_version_conflict:
            raise GlobalCountryVersionConflictError(
                "Conflicto de versión simulado."
            )

        if self.raise_update_conflict:
            raise GlobalCountryConflictError(
                "Conflicto simulado durante la actualización."
            )

        current = self.countries.get(
            country_id,
        )

        if current is None:
            return None

        now = datetime.now(
            UTC,
        )

        updated = GlobalCountry(
            id=current.id,
            iso2_code=iso2_code,
            iso3_code=iso3_code,
            name=name,
            phone_prefix=phone_prefix,
            status=status,
            version=current.version + 1,
            created_by=current.created_by,
            updated_by=actor_id,
            created_at=current.created_at,
            updated_at=now,
        )

        self.countries[country_id] = updated

        return updated

    def delete(
        self,
        country_id: UUID,
    ) -> bool:
        """Elimina un país del repositorio falso.

        Args:
            country_id: Identificador del país.

        Returns:
            True cuando existía y fue eliminado o False cuando no existía.
        """
        country = self.countries.pop(
            country_id,
            None,
        )

        return country is not None


def build_country(
    *,
    country_id: UUID | None = None,
    name: str = "Colombia",
    version: int = 1,
    created_by: str = "user-created",
    updated_by: str = "user-created",
) -> GlobalCountry:
    """Construye una entidad GlobalCountry para utilizarla en pruebas.

    Args:
        country_id: Identificador opcional del país.
        name: Nombre que tendrá el país.
        version: Versión inicial del registro.
        created_by: Usuario que creó el registro.
        updated_by: Usuario que realizó la última modificación.

    Returns:
        Entidad GlobalCountry preparada para una prueba.
    """
    now = datetime.now(
        UTC,
    )

    return GlobalCountry(
        id=country_id or uuid4(),
        iso2_code="CO",
        iso3_code="COL",
        name=name,
        phone_prefix="+57",
        status="ACTIVE",
        version=version,
        created_by=created_by,
        updated_by=updated_by,
        created_at=now,
        updated_at=now,
    )


def test_list_all_returns_repository_countries() -> None:
    """Comprueba que el servicio entregue los países del repositorio."""
    colombia = build_country()
    mexico = build_country(
        name="México",
    )

    repository = FakeGlobalCountryRepository(
        [
            colombia,
            mexico,
        ]
    )

    service = GlobalCountryService(
        repository,
    )

    result = service.list_all()

    assert result == [
        colombia,
        mexico,
    ]


def test_get_by_id_returns_existing_country() -> None:
    """Comprueba la consulta de un país existente por identificador."""
    colombia = build_country()

    repository = FakeGlobalCountryRepository(
        [colombia]
    )

    service = GlobalCountryService(
        repository,
    )

    result = service.get_by_id(
        colombia.id,
    )

    assert result == colombia


def test_get_by_id_raises_not_found_when_country_does_not_exist() -> None:
    """Comprueba que consultar un país inexistente produzca NotFound."""
    repository = FakeGlobalCountryRepository()
    service = GlobalCountryService(
        repository,
    )

    with pytest.raises(
        GlobalCountryNotFoundError,
    ):
        service.get_by_id(
            uuid4(),
        )


def test_create_forwards_actor_and_creates_audited_country() -> None:
    """Comprueba creación y propagación del usuario autenticado."""
    repository = FakeGlobalCountryRepository()
    service = GlobalCountryService(
        repository,
    )

    actor_id = "keycloak-sub-user-001"

    result = service.create(
        iso2_code="CO",
        iso3_code="COL",
        name="Colombia",
        phone_prefix="+57",
        status="ACTIVE",
        actor_id=actor_id,
    )

    assert result.iso2_code == "CO"
    assert result.iso3_code == "COL"
    assert result.name == "Colombia"
    assert result.phone_prefix == "+57"
    assert result.status == "ACTIVE"

    assert result.created_by == actor_id
    assert result.updated_by == actor_id
    assert repository.last_create_actor_id == actor_id


def test_create_propagates_repository_conflict() -> None:
    """Comprueba que un conflicto de creación no sea ocultado."""
    repository = FakeGlobalCountryRepository()
    repository.raise_create_conflict = True

    service = GlobalCountryService(
        repository,
    )

    with pytest.raises(
        GlobalCountryConflictError,
        match="Conflicto simulado durante la creación",
    ):
        service.create(
            iso2_code="CO",
            iso3_code="COL",
            name="Colombia",
            phone_prefix="+57",
            status="ACTIVE",
            actor_id="user-001",
        )


def test_update_returns_updated_country() -> None:
    """Comprueba la actualización completa de un país existente."""
    colombia = build_country(
        version=1,
        created_by="creator-user",
        updated_by="creator-user",
    )

    repository = FakeGlobalCountryRepository(
        [colombia]
    )

    service = GlobalCountryService(
        repository,
    )

    result = service.update(
        colombia.id,
        expected_version=1,
        iso2_code="CO",
        iso3_code="COL",
        name="República de Colombia",
        phone_prefix="+57",
        status="ACTIVE",
        actor_id="editor-user",
    )

    assert result.id == colombia.id
    assert result.name == "República de Colombia"

    assert result.version == 2

    assert result.created_by == "creator-user"
    assert result.updated_by == "editor-user"

    assert repository.last_expected_version == 1
    assert repository.last_update_actor_id == "editor-user"


def test_update_raises_not_found_when_country_does_not_exist() -> None:
    """Comprueba que actualizar un país inexistente produzca NotFound."""
    repository = FakeGlobalCountryRepository()

    service = GlobalCountryService(
        repository,
    )

    with pytest.raises(
        GlobalCountryNotFoundError,
    ):
        service.update(
            uuid4(),
            expected_version=1,
            iso2_code="CO",
            iso3_code="COL",
            name="Colombia",
            phone_prefix="+57",
            status="ACTIVE",
            actor_id="editor-user",
        )


def test_update_propagates_version_conflict() -> None:
    """Comprueba la propagación de conflictos de concurrencia."""
    colombia = build_country(
        version=2,
    )

    repository = FakeGlobalCountryRepository(
        [colombia]
    )

    repository.raise_version_conflict = True

    service = GlobalCountryService(
        repository,
    )

    with pytest.raises(
        GlobalCountryVersionConflictError,
        match="Conflicto de versión simulado",
    ):
        service.update(
            colombia.id,
            expected_version=1,
            iso2_code="CO",
            iso3_code="COL",
            name="Colombia",
            phone_prefix="+57",
            status="ACTIVE",
            actor_id="editor-user",
        )


def test_update_propagates_repository_conflict() -> None:
    """Comprueba la propagación de conflictos de integridad al actualizar."""
    colombia = build_country()

    repository = FakeGlobalCountryRepository(
        [colombia]
    )

    repository.raise_update_conflict = True

    service = GlobalCountryService(
        repository,
    )

    with pytest.raises(
        GlobalCountryConflictError,
        match="Conflicto simulado durante la actualización",
    ):
        service.update(
            colombia.id,
            expected_version=1,
            iso2_code="CO",
            iso3_code="COL",
            name="Colombia",
            phone_prefix="+57",
            status="ACTIVE",
            actor_id="editor-user",
        )


def test_delete_removes_existing_country() -> None:
    """Comprueba que el servicio permita eliminar un país existente."""
    colombia = build_country()

    repository = FakeGlobalCountryRepository(
        [colombia]
    )

    service = GlobalCountryService(
        repository,
    )

    service.delete(
        colombia.id,
    )

    assert repository.get_by_id(
        colombia.id,
    ) is None


def test_delete_raises_not_found_when_country_does_not_exist() -> None:
    """Comprueba que eliminar un país inexistente produzca NotFound."""
    repository = FakeGlobalCountryRepository()

    service = GlobalCountryService(
        repository,
    )

    with pytest.raises(
        GlobalCountryNotFoundError,
    ):
        service.delete(
            uuid4(),
        )
