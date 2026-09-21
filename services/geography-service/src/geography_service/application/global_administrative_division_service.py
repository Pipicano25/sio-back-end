from uuid import UUID

from geography_service.application.exceptions import (
    GlobalAdministrativeDivisionNotFoundError,
)
from geography_service.application.ports import (
    GlobalAdministrativeDivisionRepository,
)
from geography_service.domain.global_administrative_division import (
    AdministrativeDivisionStatus,
    AdministrativeDivisionType,
    GlobalAdministrativeDivision,
)
from geography_service.application.pagination import (
    PageResult,
)


class GlobalAdministrativeDivisionService:
    def __init__(
        self,
        repository: GlobalAdministrativeDivisionRepository,
    ) -> None:
        self.repository = repository

    def list_all(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None = None,
        country_id: UUID | None = None,
        parent_division_id: UUID | None = None,
        division_type: AdministrativeDivisionType | None = None,
        status: AdministrativeDivisionStatus | None = None,
    ) -> PageResult[GlobalAdministrativeDivision]:
        """Obtiene divisiones administrativas filtradas.

        Args:
            page: Página solicitada.
            page_size: Cantidad máxima de registros.
            search: Texto libre.
            country_id: Identificador del país.
            parent_division_id: División superior.
            division_type: Tipo administrativo.
            status: Estado funcional.

        Returns:
            Página filtrada de divisiones.
        """
        return self.repository.list_all(
            page=page,
            page_size=page_size,
            search=search,
            country_id=country_id,
            parent_division_id=parent_division_id,
            division_type=division_type,
            status=status,
        )

    def get_by_id(
        self,
        division_id: UUID,
    ) -> GlobalAdministrativeDivision:
        division = self.repository.get_by_id(
            division_id,
        )

        if division is None:
            raise GlobalAdministrativeDivisionNotFoundError

        return division

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
        return self.repository.create(
            country_id=country_id,
            parent_division_id=parent_division_id,
            code=code,
            name=name,
            division_type=division_type,
            status=status,
            actor_id=actor_id,
        )

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
    ) -> GlobalAdministrativeDivision:
        division = self.repository.update(
            division_id,
            expected_version=expected_version,
            country_id=country_id,
            parent_division_id=parent_division_id,
            code=code,
            name=name,
            division_type=division_type,
            status=status,
            actor_id=actor_id,
        )

        if division is None:
            raise GlobalAdministrativeDivisionNotFoundError

        return division

    def delete(
        self,
        division_id: UUID,
    ) -> None:
        deleted = self.repository.delete(
            division_id,
        )

        if not deleted:
            raise GlobalAdministrativeDivisionNotFoundError
