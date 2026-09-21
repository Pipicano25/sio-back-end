"""Pruebas unitarias para los casos de uso de divisiones administrativas."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from geography_service.application.exceptions import (
    GlobalAdministrativeDivisionConflictError,
    GlobalAdministrativeDivisionInvalidParentError,
    GlobalAdministrativeDivisionNotFoundError,
    GlobalAdministrativeDivisionVersionConflictError,
)
from geography_service.application.global_administrative_division_service import (
    GlobalAdministrativeDivisionService,
)
from geography_service.domain.global_administrative_division import (
    AdministrativeDivisionStatus,
    AdministrativeDivisionType,
    GlobalAdministrativeDivision,
)


class FakeGlobalAdministrativeDivisionRepository:
    """Repositorio falso para probar divisiones administrativas.

    El repositorio mantiene sus registros únicamente en memoria. También
    permite simular conflictos que en producción serían detectados por la
    capa de persistencia.

    Attributes:
        divisions: Divisiones almacenadas en memoria.
        last_create_actor_id: Usuario recibido durante la última creación.
        last_update_actor_id: Usuario recibido durante la última actualización.
        last_expected_version: Versión recibida durante la última actualización.
    """

    def __init__(
        self,
        divisions: list[GlobalAdministrativeDivision] | None = None,
    ) -> None:
        """Inicializa el repositorio falso.

        Args:
            divisions: Divisiones administrativas disponibles inicialmente.
        """
        self.divisions = {
            division.id: division
            for division in (divisions or [])
        }

        self.last_create_actor_id: str | None = None
        self.last_update_actor_id: str | None = None
        self.last_expected_version: int | None = None

        self.raise_create_conflict = False
        self.raise_create_invalid_parent = False

        self.raise_update_conflict = False
        self.raise_update_invalid_parent = False
        self.raise_version_conflict = False

        self.raise_delete_conflict = False

    def list_all(
        self,
    ) -> list[GlobalAdministrativeDivision]:
        """Obtiene todas las divisiones almacenadas.

        Returns:
            Lista de divisiones administrativas disponibles.
        """
        return list(
            self.divisions.values(),
        )

    def get_by_id(
        self,
        division_id: UUID,
    ) -> GlobalAdministrativeDivision | None:
        """Obtiene una división por identificador.

        Args:
            division_id: Identificador de la división.

        Returns:
            División encontrada o None cuando no existe.
        """
        return self.divisions.get(
            division_id,
        )

    def create(
        self,
        *,
        country_id: UUID,
        parent_division_id: UUID | None,
        code: str,
        name: str,
        division_type: AdministrativeDivisionType,
        status: AdministrativeDivisionStatus,
        actor_id: str,
    ) -> GlobalAdministrativeDivision:
        """Crea una división administrativa en memoria.

        Args:
            country_id: País al que pertenece la división.
            parent_division_id: División administrativa superior opcional.
            code: Código de la división.
            name: Nombre oficial.
            division_type: Tipo de división administrativa.
            status: Estado funcional.
            actor_id: Usuario autenticado que crea el registro.

        Returns:
            División administrativa creada.

        Raises:
            GlobalAdministrativeDivisionConflictError: Si se configuró un
                conflicto durante la creación.
            GlobalAdministrativeDivisionInvalidParentError: Si se configuró
                una división superior inválida.
        """
        if self.raise_create_invalid_parent:
            raise GlobalAdministrativeDivisionInvalidParentError(
                "Parent inválido simulado."
            )

        if self.raise_create_conflict:
            raise GlobalAdministrativeDivisionConflictError(
                "Conflicto simulado durante la creación."
            )

        self.last_create_actor_id = actor_id

        now = datetime.now(
            UTC,
        )

        division = GlobalAdministrativeDivision(
            id=uuid4(),
            country_id=country_id,
            parent_division_id=parent_division_id,
            code=code,
            name=name,
            division_type=division_type,
            status=status,
            version=1,
            created_by=actor_id,
            updated_by=actor_id,
            created_at=now,
            updated_at=now,
        )

        self.divisions[
            division.id
        ] = division

        return division

    def update(
        self,
        division_id: UUID,
        *,
        expected_version: int,
        country_id: UUID,
        parent_division_id: UUID | None,
        code: str,
        name: str,
        division_type: AdministrativeDivisionType,
        status: AdministrativeDivisionStatus,
        actor_id: str,
    ) -> GlobalAdministrativeDivision | None:
        """Actualiza una división administrativa en memoria.

        Args:
            division_id: Identificador de la división.
            expected_version: Versión conocida por el cliente.
            country_id: País asociado.
            parent_division_id: División superior opcional.
            code: Código administrativo.
            name: Nombre oficial.
            division_type: Tipo de división.
            status: Estado funcional.
            actor_id: Usuario autenticado que realiza la modificación.

        Returns:
            División actualizada o None cuando no existe.

        Raises:
            GlobalAdministrativeDivisionConflictError: Si se configuró un
                conflicto de integridad.
            GlobalAdministrativeDivisionInvalidParentError: Si se configuró
                un parent inválido.
            GlobalAdministrativeDivisionVersionConflictError: Si se configuró
                un conflicto de concurrencia.
        """
        self.last_update_actor_id = actor_id
        self.last_expected_version = expected_version

        if self.raise_version_conflict:
            raise GlobalAdministrativeDivisionVersionConflictError(
                "Conflicto de versión simulado."
            )

        if self.raise_update_invalid_parent:
            raise GlobalAdministrativeDivisionInvalidParentError(
                "Parent inválido simulado."
            )

        if self.raise_update_conflict:
            raise GlobalAdministrativeDivisionConflictError(
                "Conflicto simulado durante la actualización."
            )

        current = self.divisions.get(
            division_id,
        )

        if current is None:
            return None

        now = datetime.now(
            UTC,
        )

        updated = GlobalAdministrativeDivision(
            id=current.id,
            country_id=country_id,
            parent_division_id=parent_division_id,
            code=code,
            name=name,
            division_type=division_type,
            status=status,
            version=current.version + 1,
            created_by=current.created_by,
            updated_by=actor_id,
            created_at=current.created_at,
            updated_at=now,
        )

        self.divisions[
            division_id
        ] = updated

        return updated

    def delete(
        self,
        division_id: UUID,
    ) -> bool:
        """Elimina una división administrativa del repositorio falso.

        Args:
            division_id: Identificador de la división.

        Returns:
            True si fue eliminada o False cuando no existía.

        Raises:
            GlobalAdministrativeDivisionConflictError: Si la prueba configuró
                un conflicto durante la eliminación.
        """
        if self.raise_delete_conflict:
            raise GlobalAdministrativeDivisionConflictError(
                "Conflicto simulado durante la eliminación."
            )

        division = self.divisions.pop(
            division_id,
            None,
        )

        return division is not None


def build_division(
    *,
    division_id: UUID | None = None,
    country_id: UUID | None = None,
    parent_division_id: UUID | None = None,
    code: str = "ANT",
    name: str = "Antioquia",
    division_type: AdministrativeDivisionType = "DEPARTMENT",
    status: AdministrativeDivisionStatus = "ACTIVE",
    version: int = 1,
    created_by: str = "creator-user",
    updated_by: str = "creator-user",
) -> GlobalAdministrativeDivision:
    """Construye una división administrativa para utilizarla en pruebas.

    Args:
        division_id: Identificador opcional de la división.
        country_id: Identificador opcional del país.
        parent_division_id: División administrativa superior opcional.
        code: Código administrativo.
        name: Nombre oficial.
        division_type: Tipo de división.
        status: Estado funcional.
        version: Versión inicial.
        created_by: Usuario que creó el registro.
        updated_by: Usuario que realizó la última modificación.

    Returns:
        Entidad GlobalAdministrativeDivision preparada para testing.
    """
    now = datetime.now(
        UTC,
    )

    return GlobalAdministrativeDivision(
        id=division_id or uuid4(),
        country_id=country_id or uuid4(),
        parent_division_id=parent_division_id,
        code=code,
        name=name,
        division_type=division_type,
        status=status,
        version=version,
        created_by=created_by,
        updated_by=updated_by,
        created_at=now,
        updated_at=now,
    )


def test_list_all_returns_repository_divisions() -> None:
    """Comprueba que el servicio entregue las divisiones del repositorio."""
    country_id = uuid4()

    antioquia = build_division(
        country_id=country_id,
        code="ANT",
        name="Antioquia",
    )

    cundinamarca = build_division(
        country_id=country_id,
        code="CUN",
        name="Cundinamarca",
    )

    repository = FakeGlobalAdministrativeDivisionRepository(
        [
            antioquia,
            cundinamarca,
        ]
    )

    service = GlobalAdministrativeDivisionService(
        repository,
    )

    result = service.list_all()

    assert result == [
        antioquia,
        cundinamarca,
    ]


def test_get_by_id_returns_existing_division() -> None:
    """Comprueba la consulta de una división administrativa existente."""
    antioquia = build_division()

    repository = FakeGlobalAdministrativeDivisionRepository(
        [antioquia]
    )

    service = GlobalAdministrativeDivisionService(
        repository,
    )

    result = service.get_by_id(
        antioquia.id,
    )

    assert result == antioquia


def test_get_by_id_raises_not_found_when_division_does_not_exist() -> None:
    """Comprueba que consultar una división inexistente produzca NotFound."""
    repository = FakeGlobalAdministrativeDivisionRepository()

    service = GlobalAdministrativeDivisionService(
        repository,
    )

    with pytest.raises(
        GlobalAdministrativeDivisionNotFoundError,
    ):
        service.get_by_id(
            uuid4(),
        )


def test_create_forwards_actor_and_creates_audited_division() -> None:
    """Comprueba creación y propagación del usuario autenticado."""
    repository = FakeGlobalAdministrativeDivisionRepository()

    service = GlobalAdministrativeDivisionService(
        repository,
    )

    country_id = uuid4()
    actor_id = "keycloak-sub-user-001"

    result = service.create(
        country_id=country_id,
        parent_division_id=None,
        code="ANT",
        name="Antioquia",
        division_type="DEPARTMENT",
        status="ACTIVE",
        actor_id=actor_id,
    )

    assert result.country_id == country_id
    assert result.parent_division_id is None
    assert result.code == "ANT"
    assert result.name == "Antioquia"
    assert result.division_type == "DEPARTMENT"
    assert result.status == "ACTIVE"

    assert result.version == 1
    assert result.created_by == actor_id
    assert result.updated_by == actor_id

    assert repository.last_create_actor_id == actor_id


def test_create_accepts_parent_division() -> None:
    """Comprueba que el servicio propague una división superior válida."""
    repository = FakeGlobalAdministrativeDivisionRepository()

    service = GlobalAdministrativeDivisionService(
        repository,
    )

    country_id = uuid4()
    parent_id = uuid4()

    result = service.create(
        country_id=country_id,
        parent_division_id=parent_id,
        code="SUB-001",
        name="Subdivisión",
        division_type="DISTRICT",
        status="ACTIVE",
        actor_id="creator-user",
    )

    assert result.country_id == country_id
    assert result.parent_division_id == parent_id


def test_create_propagates_invalid_parent_error() -> None:
    """Comprueba la propagación de un parent administrativo inválido."""
    repository = FakeGlobalAdministrativeDivisionRepository()
    repository.raise_create_invalid_parent = True

    service = GlobalAdministrativeDivisionService(
        repository,
    )

    with pytest.raises(
        GlobalAdministrativeDivisionInvalidParentError,
        match="Parent inválido simulado",
    ):
        service.create(
            country_id=uuid4(),
            parent_division_id=uuid4(),
            code="TEST",
            name="División inválida",
            division_type="OTHER",
            status="ACTIVE",
            actor_id="creator-user",
        )


def test_create_propagates_repository_conflict() -> None:
    """Comprueba la propagación de conflictos durante la creación."""
    repository = FakeGlobalAdministrativeDivisionRepository()
    repository.raise_create_conflict = True

    service = GlobalAdministrativeDivisionService(
        repository,
    )

    with pytest.raises(
        GlobalAdministrativeDivisionConflictError,
        match="Conflicto simulado durante la creación",
    ):
        service.create(
            country_id=uuid4(),
            parent_division_id=None,
            code="ANT",
            name="Antioquia",
            division_type="DEPARTMENT",
            status="ACTIVE",
            actor_id="creator-user",
        )


def test_update_returns_updated_division() -> None:
    """Comprueba la actualización completa de una división existente."""
    country_id = uuid4()

    antioquia = build_division(
        country_id=country_id,
        version=1,
        created_by="creator-user",
    )

    repository = FakeGlobalAdministrativeDivisionRepository(
        [antioquia]
    )

    service = GlobalAdministrativeDivisionService(
        repository,
    )

    result = service.update(
        antioquia.id,
        expected_version=1,
        country_id=country_id,
        parent_division_id=None,
        code="ANT",
        name="Departamento de Antioquia",
        division_type="DEPARTMENT",
        status="ACTIVE",
        actor_id="editor-user",
    )

    assert result.id == antioquia.id
    assert result.name == "Departamento de Antioquia"

    assert result.version == 2

    assert result.created_by == "creator-user"
    assert result.updated_by == "editor-user"

    assert repository.last_expected_version == 1
    assert repository.last_update_actor_id == "editor-user"


def test_update_can_assign_parent_division() -> None:
    """Comprueba que una actualización pueda asignar una división superior."""
    country_id = uuid4()
    parent_id = uuid4()

    division = build_division(
        country_id=country_id,
    )

    repository = FakeGlobalAdministrativeDivisionRepository(
        [division]
    )

    service = GlobalAdministrativeDivisionService(
        repository,
    )

    result = service.update(
        division.id,
        expected_version=1,
        country_id=country_id,
        parent_division_id=parent_id,
        code=division.code,
        name=division.name,
        division_type=division.division_type,
        status=division.status,
        actor_id="editor-user",
    )

    assert result.parent_division_id == parent_id


def test_update_raises_not_found_when_division_does_not_exist() -> None:
    """Comprueba que actualizar una división inexistente produzca NotFound."""
    repository = FakeGlobalAdministrativeDivisionRepository()

    service = GlobalAdministrativeDivisionService(
        repository,
    )

    with pytest.raises(
        GlobalAdministrativeDivisionNotFoundError,
    ):
        service.update(
            uuid4(),
            expected_version=1,
            country_id=uuid4(),
            parent_division_id=None,
            code="ANT",
            name="Antioquia",
            division_type="DEPARTMENT",
            status="ACTIVE",
            actor_id="editor-user",
        )


def test_update_propagates_version_conflict() -> None:
    """Comprueba la propagación de conflictos de concurrencia."""
    division = build_division(
        version=2,
    )

    repository = FakeGlobalAdministrativeDivisionRepository(
        [division]
    )

    repository.raise_version_conflict = True

    service = GlobalAdministrativeDivisionService(
        repository,
    )

    with pytest.raises(
        GlobalAdministrativeDivisionVersionConflictError,
        match="Conflicto de versión simulado",
    ):
        service.update(
            division.id,
            expected_version=1,
            country_id=division.country_id,
            parent_division_id=None,
            code=division.code,
            name=division.name,
            division_type=division.division_type,
            status=division.status,
            actor_id="editor-user",
        )


def test_update_propagates_invalid_parent_error() -> None:
    """Comprueba la propagación de un parent inválido al actualizar."""
    division = build_division()

    repository = FakeGlobalAdministrativeDivisionRepository(
        [division]
    )

    repository.raise_update_invalid_parent = True

    service = GlobalAdministrativeDivisionService(
        repository,
    )

    with pytest.raises(
        GlobalAdministrativeDivisionInvalidParentError,
        match="Parent inválido simulado",
    ):
        service.update(
            division.id,
            expected_version=1,
            country_id=division.country_id,
            parent_division_id=uuid4(),
            code=division.code,
            name=division.name,
            division_type=division.division_type,
            status=division.status,
            actor_id="editor-user",
        )


def test_update_propagates_repository_conflict() -> None:
    """Comprueba la propagación de conflictos de integridad al actualizar."""
    division = build_division()

    repository = FakeGlobalAdministrativeDivisionRepository(
        [division]
    )

    repository.raise_update_conflict = True

    service = GlobalAdministrativeDivisionService(
        repository,
    )

    with pytest.raises(
        GlobalAdministrativeDivisionConflictError,
        match="Conflicto simulado durante la actualización",
    ):
        service.update(
            division.id,
            expected_version=1,
            country_id=division.country_id,
            parent_division_id=None,
            code=division.code,
            name=division.name,
            division_type=division.division_type,
            status=division.status,
            actor_id="editor-user",
        )


def test_delete_removes_existing_division() -> None:
    """Comprueba la eliminación de una división existente."""
    division = build_division()

    repository = FakeGlobalAdministrativeDivisionRepository(
        [division]
    )

    service = GlobalAdministrativeDivisionService(
        repository,
    )

    service.delete(
        division.id,
    )

    assert repository.get_by_id(
        division.id,
    ) is None


def test_delete_raises_not_found_when_division_does_not_exist() -> None:
    """Comprueba que eliminar una división inexistente produzca NotFound."""
    repository = FakeGlobalAdministrativeDivisionRepository()

    service = GlobalAdministrativeDivisionService(
        repository,
    )

    with pytest.raises(
        GlobalAdministrativeDivisionNotFoundError,
    ):
        service.delete(
            uuid4(),
        )


def test_delete_propagates_repository_conflict() -> None:
    """Comprueba la propagación de conflictos durante la eliminación."""
    division = build_division()

    repository = FakeGlobalAdministrativeDivisionRepository(
        [division]
    )

    repository.raise_delete_conflict = True

    service = GlobalAdministrativeDivisionService(
        repository,
    )

    with pytest.raises(
        GlobalAdministrativeDivisionConflictError,
        match="Conflicto simulado durante la eliminación",
    ):
        service.delete(
            division.id,
        )
