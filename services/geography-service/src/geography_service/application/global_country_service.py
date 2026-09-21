from uuid import UUID

from geography_service.application.exceptions import (
    GlobalCountryNotFoundError,
)
from geography_service.application.ports import (
    GlobalCountryRepository,
)
from geography_service.domain.global_country import (
    GlobalCountry,
    GlobalCountryStatus,
)
from geography_service.application.pagination import (
    PageResult,
)


class GlobalCountryService:
    def __init__(
        self,
        repository: GlobalCountryRepository,
    ) -> None:
        self.repository = repository

    def list_all(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None = None,
        iso2_code: str | None = None,
        iso3_code: str | None = None,
        status: GlobalCountryStatus | None = None,
    ) -> PageResult[GlobalCountry]:
        """Obtiene países globales utilizando paginación y filtros.

        Args:
            page: Página solicitada.
            page_size: Cantidad máxima de registros.
            search: Texto libre.
            iso2_code: Código ISO2 exacto.
            iso3_code: Código ISO3 exacto.
            status: Estado funcional.

        Returns:
            Página filtrada de países globales.
        """
        return self.repository.list_all(
            page=page,
            page_size=page_size,
            search=search,
            iso2_code=iso2_code,
            iso3_code=iso3_code,
            status=status,
        )

    def get_by_id(
        self,
        country_id: UUID,
    ) -> GlobalCountry:
        country = self.repository.get_by_id(
            country_id,
        )

        if country is None:
            raise GlobalCountryNotFoundError

        return country

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
        return self.repository.create(
            iso2_code=iso2_code,
            iso3_code=iso3_code,
            name=name,
            phone_prefix=phone_prefix,
            status=status,
            actor_id=actor_id,
        )

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
    ) -> GlobalCountry:
        country = self.repository.update(
            country_id,
            expected_version=expected_version,
            iso2_code=iso2_code,
            iso3_code=iso3_code,
            name=name,
            phone_prefix=phone_prefix,
            status=status,
            actor_id=actor_id,
        )

        if country is None:
            raise GlobalCountryNotFoundError

        return country

    def delete(
        self,
        country_id: UUID,
    ) -> None:
        deleted = self.repository.delete(
            country_id,
        )

        if not deleted:
            raise GlobalCountryNotFoundError