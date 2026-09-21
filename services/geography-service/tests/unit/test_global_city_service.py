"""Pruebas unitarias para los casos de uso de ciudades globales."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from geography_service.application.exceptions import (
    GlobalCityConflictError,
    GlobalCityInvalidAdministrativeDivisionError,
    GlobalCityNotFoundError,
    GlobalCityVersionConflictError,
)
from geography_service.application.global_city_service import (
    GlobalCityService,
)
from geography_service.domain.global_city import (
    GlobalCity,
    GlobalCityStatus,
)


class FakeGlobalCityRepository:
    """Repositorio falso utilizado para probar GlobalCityService.

    El repositorio almacena las ciudades únicamente en memoria y permite
    simular errores que, en producción, serían producidos por la capa de
    persistencia.

    Attributes:
        cities: Ciudades almacenadas en memoria.
        last_create_actor_id: Usuario recibido en la última creación.
        last_update_actor_id: Usuario recibido en la última actualización.
        last_expected_version: Versión recibida en la última actualización.
    """

    def __init__(
        self,
        cities: list[GlobalCity] | None = None,
    ) -> None:
        """Inicializa el repositorio falso.

        Args:
            cities: Ciudades disponibles inicialmente.
        """
        self.cities = {
            city.id: city
            for city in (cities or [])
        }

        self.last_create_actor_id: str | None = None
        self.last_update_actor_id: str | None = None
        self.last_expected_version: int | None = None

        self.raise_create_conflict = False
        self.raise_create_invalid_division = False

        self.raise_update_conflict = False
        self.raise_update_invalid_division = False
        self.raise_update_version_conflict = False

        self.raise_delete_conflict = False
        self.raise_delete_version_conflict = False

    def list_all(self) -> list[GlobalCity]:
        """Obtiene todas las ciudades almacenadas.

        Returns:
            Lista de ciudades disponibles en memoria.
        """
        return list(
            self.cities.values(),
        )

    def get_by_id(
        self,
        city_id: UUID,
    ) -> GlobalCity | None:
        """Obtiene una ciudad por identificador.

        Args:
            city_id: Identificador de la ciudad.

        Returns:
            Ciudad encontrada o None cuando no existe.
        """
        return self.cities.get(
            city_id,
        )

    def create(
        self,
        *,
        country_id: UUID,
        administrative_division_id: UUID | None,
        code: str | None,
        name: str,
        latitude: Decimal | None,
        longitude: Decimal | None,
        status: GlobalCityStatus,
        actor_id: str,
    ) -> GlobalCity:
        """Crea una ciudad dentro del repositorio falso.

        Args:
            country_id: País al que pertenece la ciudad.
            administrative_division_id: División administrativa opcional.
            code: Código oficial opcional.
            name: Nombre oficial de la ciudad.
            latitude: Latitud aproximada.
            longitude: Longitud aproximada.
            status: Estado funcional.
            actor_id: Usuario autenticado que crea el registro.

        Returns:
            Ciudad creada.

        Raises:
            GlobalCityConflictError: Si se configuró un conflicto de
                integridad.
            GlobalCityInvalidAdministrativeDivisionError: Si se configuró una
                división administrativa inválida.
        """
        if self.raise_create_invalid_division:
            raise GlobalCityInvalidAdministrativeDivisionError(
                "División administrativa inválida simulada."
            )

        if self.raise_create_conflict:
            raise GlobalCityConflictError(
                "Conflicto simulado durante la creación."
            )

        self.last_create_actor_id = actor_id

        now = datetime.now(
            UTC,
        )

        city = GlobalCity(
            id=uuid4(),
            country_id=country_id,
            administrative_division_id=administrative_division_id,
            code=code,
            name=name,
            latitude=latitude,
            longitude=longitude,
            status=status,
            version=1,
            created_by=actor_id,
            updated_by=actor_id,
            created_at=now,
            updated_at=now,
        )

        self.cities[
            city.id
        ] = city

        return city

    def update(
        self,
        city_id: UUID,
        *,
        expected_version: int,
        country_id: UUID,
        administrative_division_id: UUID | None,
        code: str | None,
        name: str,
        latitude: Decimal | None,
        longitude: Decimal | None,
        status: GlobalCityStatus,
        actor_id: str,
    ) -> GlobalCity | None:
        """Actualiza una ciudad dentro del repositorio falso.

        Args:
            city_id: Identificador de la ciudad.
            expected_version: Versión conocida por el cliente.
            country_id: País al que pertenece la ciudad.
            administrative_division_id: División administrativa opcional.
            code: Código oficial opcional.
            name: Nombre oficial.
            latitude: Latitud aproximada.
            longitude: Longitud aproximada.
            status: Estado funcional.
            actor_id: Usuario autenticado que realiza la modificación.

        Returns:
            Ciudad actualizada o None cuando no existe.

        Raises:
            GlobalCityConflictError: Si se configuró un conflicto de
                integridad.
            GlobalCityInvalidAdministrativeDivisionError: Si se configuró una
                división administrativa inválida.
            GlobalCityVersionConflictError: Si se configuró un conflicto de
                concurrencia.
        """
        self.last_update_actor_id = actor_id
        self.last_expected_version = expected_version

        if self.raise_update_version_conflict:
            raise GlobalCityVersionConflictError(
                "Conflicto de versión simulado."
            )

        if self.raise_update_invalid_division:
            raise GlobalCityInvalidAdministrativeDivisionError(
                "División administrativa inválida simulada."
            )

        if self.raise_update_conflict:
            raise GlobalCityConflictError(
                "Conflicto simulado durante la actualización."
            )

        current = self.cities.get(
            city_id,
        )

        if current is None:
            return None

        now = datetime.now(
            UTC,
        )

        updated = GlobalCity(
            id=current.id,
            country_id=country_id,
            administrative_division_id=administrative_division_id,
            code=code,
            name=name,
            latitude=latitude,
            longitude=longitude,
            status=status,
            version=current.version + 1,
            created_by=current.created_by,
            updated_by=actor_id,
            created_at=current.created_at,
            updated_at=now,
        )

        self.cities[
            city_id
        ] = updated

        return updated

    def delete(
        self,
        city_id: UUID,
    ) -> bool:
        """Elimina una ciudad del repositorio falso.

        Args:
            city_id: Identificador de la ciudad.

        Returns:
            True cuando fue eliminada o False cuando no existía.

        Raises:
            GlobalCityConflictError: Si se configuró un conflicto durante
                la eliminación.
            GlobalCityVersionConflictError: Si se configuró un conflicto
                concurrente durante la eliminación.
        """
        if self.raise_delete_version_conflict:
            raise GlobalCityVersionConflictError(
                "Conflicto de versión simulado durante la eliminación."
            )

        if self.raise_delete_conflict:
            raise GlobalCityConflictError(
                "Conflicto simulado durante la eliminación."
            )

        city = self.cities.pop(
            city_id,
            None,
        )

        return city is not None


def build_city(
    *,
    city_id: UUID | None = None,
    country_id: UUID | None = None,
    administrative_division_id: UUID | None = None,
    code: str | None = "05001",
    name: str = "Medellín",
    latitude: Decimal | None = Decimal("6.244203"),
    longitude: Decimal | None = Decimal("-75.581212"),
    status: GlobalCityStatus = "ACTIVE",
    version: int = 1,
    created_by: str = "creator-user",
    updated_by: str = "creator-user",
) -> GlobalCity:
    """Construye una ciudad global para utilizarla en pruebas.

    Args:
        city_id: Identificador opcional de la ciudad.
        country_id: Identificador opcional del país.
        administrative_division_id: División administrativa opcional.
        code: Código oficial opcional.
        name: Nombre oficial.
        latitude: Latitud aproximada.
        longitude: Longitud aproximada.
        status: Estado funcional.
        version: Versión inicial.
        created_by: Usuario creador.
        updated_by: Usuario que realizó la última modificación.

    Returns:
        Entidad GlobalCity preparada para una prueba.
    """
    now = datetime.now(
        UTC,
    )

    return GlobalCity(
        id=city_id or uuid4(),
        country_id=country_id or uuid4(),
        administrative_division_id=administrative_division_id,
        code=code,
        name=name,
        latitude=latitude,
        longitude=longitude,
        status=status,
        version=version,
        created_by=created_by,
        updated_by=updated_by,
        created_at=now,
        updated_at=now,
    )


def test_list_all_returns_repository_cities() -> None:
    """Comprueba que el servicio entregue las ciudades del repositorio."""
    country_id = uuid4()

    medellin = build_city(
        country_id=country_id,
        code="05001",
        name="Medellín",
    )

    bogota = build_city(
        country_id=country_id,
        code="11001",
        name="Bogotá",
        latitude=Decimal("4.711000"),
        longitude=Decimal("-74.072100"),
    )

    repository = FakeGlobalCityRepository(
        [
            medellin,
            bogota,
        ]
    )

    service = GlobalCityService(
        repository,
    )

    result = service.list_all()

    assert result == [
        medellin,
        bogota,
    ]


def test_get_by_id_returns_existing_city() -> None:
    """Comprueba la consulta de una ciudad existente."""
    medellin = build_city()

    repository = FakeGlobalCityRepository(
        [medellin]
    )

    service = GlobalCityService(
        repository,
    )

    result = service.get_by_id(
        medellin.id,
    )

    assert result == medellin


def test_get_by_id_raises_not_found_when_city_does_not_exist() -> None:
    """Comprueba que consultar una ciudad inexistente produzca NotFound."""
    repository = FakeGlobalCityRepository()

    service = GlobalCityService(
        repository,
    )

    with pytest.raises(
        GlobalCityNotFoundError,
    ):
        service.get_by_id(
            uuid4(),
        )


def test_create_forwards_actor_and_creates_audited_city() -> None:
    """Comprueba creación y propagación del usuario autenticado."""
    repository = FakeGlobalCityRepository()

    service = GlobalCityService(
        repository,
    )

    country_id = uuid4()
    division_id = uuid4()
    actor_id = "keycloak-sub-user-001"

    result = service.create(
        country_id=country_id,
        administrative_division_id=division_id,
        code="05001",
        name="Medellín",
        latitude=Decimal("6.244203"),
        longitude=Decimal("-75.581212"),
        status="ACTIVE",
        actor_id=actor_id,
    )

    assert result.country_id == country_id
    assert result.administrative_division_id == division_id
    assert result.code == "05001"
    assert result.name == "Medellín"

    assert result.latitude == Decimal(
        "6.244203"
    )
    assert result.longitude == Decimal(
        "-75.581212"
    )

    assert result.status == "ACTIVE"
    assert result.version == 1

    assert result.created_by == actor_id
    assert result.updated_by == actor_id

    assert repository.last_create_actor_id == actor_id


def test_create_accepts_city_without_administrative_division() -> None:
    """Comprueba que una ciudad pueda no tener división administrativa."""
    repository = FakeGlobalCityRepository()

    service = GlobalCityService(
        repository,
    )

    result = service.create(
        country_id=uuid4(),
        administrative_division_id=None,
        code=None,
        name="Ciudad sin división",
        latitude=None,
        longitude=None,
        status="ACTIVE",
        actor_id="creator-user",
    )

    assert result.administrative_division_id is None
    assert result.code is None
    assert result.latitude is None
    assert result.longitude is None


def test_create_propagates_invalid_administrative_division_error() -> None:
    """Comprueba la propagación de una división administrativa inválida."""
    repository = FakeGlobalCityRepository()
    repository.raise_create_invalid_division = True

    service = GlobalCityService(
        repository,
    )

    with pytest.raises(
        GlobalCityInvalidAdministrativeDivisionError,
        match="División administrativa inválida simulada",
    ):
        service.create(
            country_id=uuid4(),
            administrative_division_id=uuid4(),
            code="05001",
            name="Medellín",
            latitude=Decimal("6.244203"),
            longitude=Decimal("-75.581212"),
            status="ACTIVE",
            actor_id="creator-user",
        )


def test_create_propagates_repository_conflict() -> None:
    """Comprueba la propagación de conflictos durante la creación."""
    repository = FakeGlobalCityRepository()
    repository.raise_create_conflict = True

    service = GlobalCityService(
        repository,
    )

    with pytest.raises(
        GlobalCityConflictError,
        match="Conflicto simulado durante la creación",
    ):
        service.create(
            country_id=uuid4(),
            administrative_division_id=None,
            code="05001",
            name="Medellín",
            latitude=Decimal("6.244203"),
            longitude=Decimal("-75.581212"),
            status="ACTIVE",
            actor_id="creator-user",
        )


def test_update_returns_updated_city() -> None:
    """Comprueba la actualización completa de una ciudad existente."""
    country_id = uuid4()
    division_id = uuid4()

    medellin = build_city(
        country_id=country_id,
        administrative_division_id=division_id,
        version=1,
        created_by="creator-user",
        updated_by="creator-user",
    )

    repository = FakeGlobalCityRepository(
        [medellin]
    )

    service = GlobalCityService(
        repository,
    )

    result = service.update(
        medellin.id,
        expected_version=1,
        country_id=country_id,
        administrative_division_id=division_id,
        code="05001",
        name="Medellín Distrito Especial",
        latitude=Decimal("6.244203"),
        longitude=Decimal("-75.581212"),
        status="ACTIVE",
        actor_id="editor-user",
    )

    assert result.id == medellin.id
    assert result.name == "Medellín Distrito Especial"

    assert result.version == 2

    assert result.created_by == "creator-user"
    assert result.updated_by == "editor-user"

    assert repository.last_expected_version == 1
    assert repository.last_update_actor_id == "editor-user"


def test_update_can_remove_administrative_division() -> None:
    """Comprueba que una actualización pueda remover la división asociada."""
    country_id = uuid4()

    city = build_city(
        country_id=country_id,
        administrative_division_id=uuid4(),
    )

    repository = FakeGlobalCityRepository(
        [city]
    )

    service = GlobalCityService(
        repository,
    )

    result = service.update(
        city.id,
        expected_version=1,
        country_id=country_id,
        administrative_division_id=None,
        code=city.code,
        name=city.name,
        latitude=city.latitude,
        longitude=city.longitude,
        status=city.status,
        actor_id="editor-user",
    )

    assert result.administrative_division_id is None


def test_update_raises_not_found_when_city_does_not_exist() -> None:
    """Comprueba que actualizar una ciudad inexistente produzca NotFound."""
    repository = FakeGlobalCityRepository()

    service = GlobalCityService(
        repository,
    )

    with pytest.raises(
        GlobalCityNotFoundError,
    ):
        service.update(
            uuid4(),
            expected_version=1,
            country_id=uuid4(),
            administrative_division_id=None,
            code="05001",
            name="Medellín",
            latitude=Decimal("6.244203"),
            longitude=Decimal("-75.581212"),
            status="ACTIVE",
            actor_id="editor-user",
        )


def test_update_propagates_version_conflict() -> None:
    """Comprueba la propagación de conflictos de concurrencia."""
    city = build_city(
        version=2,
    )

    repository = FakeGlobalCityRepository(
        [city]
    )

    repository.raise_update_version_conflict = True

    service = GlobalCityService(
        repository,
    )

    with pytest.raises(
        GlobalCityVersionConflictError,
        match="Conflicto de versión simulado",
    ):
        service.update(
            city.id,
            expected_version=1,
            country_id=city.country_id,
            administrative_division_id=city.administrative_division_id,
            code=city.code,
            name=city.name,
            latitude=city.latitude,
            longitude=city.longitude,
            status=city.status,
            actor_id="editor-user",
        )


def test_update_propagates_invalid_administrative_division_error() -> None:
    """Comprueba la propagación de una división inválida al actualizar."""
    city = build_city()

    repository = FakeGlobalCityRepository(
        [city]
    )

    repository.raise_update_invalid_division = True

    service = GlobalCityService(
        repository,
    )

    with pytest.raises(
        GlobalCityInvalidAdministrativeDivisionError,
        match="División administrativa inválida simulada",
    ):
        service.update(
            city.id,
            expected_version=1,
            country_id=city.country_id,
            administrative_division_id=uuid4(),
            code=city.code,
            name=city.name,
            latitude=city.latitude,
            longitude=city.longitude,
            status=city.status,
            actor_id="editor-user",
        )


def test_update_propagates_repository_conflict() -> None:
    """Comprueba la propagación de conflictos de integridad al actualizar."""
    city = build_city()

    repository = FakeGlobalCityRepository(
        [city]
    )

    repository.raise_update_conflict = True

    service = GlobalCityService(
        repository,
    )

    with pytest.raises(
        GlobalCityConflictError,
        match="Conflicto simulado durante la actualización",
    ):
        service.update(
            city.id,
            expected_version=1,
            country_id=city.country_id,
            administrative_division_id=None,
            code=city.code,
            name=city.name,
            latitude=city.latitude,
            longitude=city.longitude,
            status=city.status,
            actor_id="editor-user",
        )


def test_delete_removes_existing_city() -> None:
    """Comprueba la eliminación de una ciudad existente."""
    city = build_city()

    repository = FakeGlobalCityRepository(
        [city]
    )

    service = GlobalCityService(
        repository,
    )

    service.delete(
        city.id,
    )

    assert repository.get_by_id(
        city.id,
    ) is None


def test_delete_raises_not_found_when_city_does_not_exist() -> None:
    """Comprueba que eliminar una ciudad inexistente produzca NotFound."""
    repository = FakeGlobalCityRepository()

    service = GlobalCityService(
        repository,
    )

    with pytest.raises(
        GlobalCityNotFoundError,
    ):
        service.delete(
            uuid4(),
        )


def test_delete_propagates_repository_conflict() -> None:
    """Comprueba la propagación de conflictos durante la eliminación."""
    city = build_city()

    repository = FakeGlobalCityRepository(
        [city]
    )

    repository.raise_delete_conflict = True

    service = GlobalCityService(
        repository,
    )

    with pytest.raises(
        GlobalCityConflictError,
        match="Conflicto simulado durante la eliminación",
    ):
        service.delete(
            city.id,
        )


def test_delete_propagates_version_conflict() -> None:
    """Comprueba la propagación de conflictos concurrentes al eliminar."""
    city = build_city()

    repository = FakeGlobalCityRepository(
        [city]
    )

    repository.raise_delete_version_conflict = True

    service = GlobalCityService(
        repository,
    )

    with pytest.raises(
        GlobalCityVersionConflictError,
        match="Conflicto de versión simulado durante la eliminación",
    ):
        service.delete(
            city.id,
        )
