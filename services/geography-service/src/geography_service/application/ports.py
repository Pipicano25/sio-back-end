"""Contratos de persistencia utilizados por la capa de aplicación."""

from decimal import Decimal
from typing import Protocol
from uuid import UUID

from geography_service.domain.global_country import (
    GlobalCountry,
    GlobalCountryStatus,
)
from geography_service.domain.global_administrative_division import (
    AdministrativeDivisionStatus,
    AdministrativeDivisionType,
    GlobalAdministrativeDivision,
)
from geography_service.domain.global_city import (
    GlobalCity,
    GlobalCityStatus,
)
from geography_service.application.pagination import (
    PageResult,
)


class GlobalCountryRepository(Protocol):
    def list_all(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None,
        iso2_code: str | None,
        iso3_code: str | None,
        status: GlobalCountryStatus | None,
    ) -> PageResult[GlobalCountry]:
        """Obtiene una página filtrada de países globales.

        Args:
            page: Página solicitada.
            page_size: Cantidad máxima de registros.
            search: Texto libre de búsqueda.
            iso2_code: Código ISO2 exacto.
            iso3_code: Código ISO3 exacto.
            status: Estado funcional.

        Returns:
            Página filtrada de países.
        """
        ...

    def get_by_id(
        self,
        country_id: UUID,
    ) -> GlobalCountry | None:
        ...

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
        ...

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
        ...

    def delete(
        self,
        country_id: UUID,
    ) -> bool:
        ...


class GlobalAdministrativeDivisionRepository(Protocol):
    def list_all(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None,
        country_id: UUID | None,
        parent_division_id: UUID | None,
        division_type: AdministrativeDivisionType | None,
        status: AdministrativeDivisionStatus | None,
    ) -> PageResult[GlobalAdministrativeDivision]:
        """Obtiene divisiones administrativas filtradas.

        Args:
            page: Página solicitada.
            page_size: Cantidad máxima de registros.
            search: Texto libre.
            country_id: País propietario.
            parent_division_id: División superior.
            division_type: Tipo administrativo.
            status: Estado funcional.

        Returns:
            Página filtrada de divisiones.
        """
        ...

    def get_by_id(
        self,
        division_id: UUID,
    ) -> GlobalAdministrativeDivision | None:
        ...

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
        ...

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
        ...

    def delete(
        self,
        division_id: UUID,
    ) -> bool:
        ...


class GlobalCityRepository(Protocol):
    """Define las operaciones de persistencia requeridas para ciudades globales."""

    def list_all(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None,
        country_id: UUID | None,
        administrative_division_id: UUID | None,
        code: str | None,
        status: GlobalCityStatus | None,
    ) -> PageResult[GlobalCity]:
        """Obtiene ciudades globales filtradas.

        Args:
            page: Página solicitada.
            page_size: Cantidad máxima de registros.
            search: Texto libre.
            country_id: País propietario.
            administrative_division_id: División administrativa.
            code: Código exacto.
            status: Estado funcional.

        Returns:
            Página filtrada de ciudades.
        """
        ...

    def get_by_id(
        self,
        city_id: UUID,
    ) -> GlobalCity | None:
        """Obtiene una ciudad global por su identificador.

        Args:
            city_id: Identificador de la ciudad.

        Returns:
            La ciudad encontrada o None cuando no existe.
        """
        ...

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
        """Crea una ciudad global.

        Args:
            country_id: País al que pertenece la ciudad.
            administrative_division_id: División administrativa asociada.
            code: Código oficial cuando exista.
            name: Nombre oficial de la ciudad.
            latitude: Latitud aproximada.
            longitude: Longitud aproximada.
            status: Estado inicial.
            actor_id: Identificador del usuario autenticado.

        Returns:
            Ciudad creada.
        """
        ...

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
        """Actualiza completamente una ciudad global.

        Args:
            city_id: Identificador de la ciudad.
            expected_version: Versión conocida por el cliente.
            country_id: País al que pertenece la ciudad.
            administrative_division_id: División administrativa asociada.
            code: Código oficial cuando exista.
            name: Nombre oficial.
            latitude: Latitud aproximada.
            longitude: Longitud aproximada.
            status: Estado funcional.
            actor_id: Usuario que realiza la modificación.

        Returns:
            Ciudad actualizada o None cuando no existe.

        Raises:
            GlobalCityVersionConflictError: Si la versión no coincide.
        """
        ...

    def delete(
        self,
        city_id: UUID,
    ) -> bool:
        """Elimina físicamente una ciudad global.

        Args:
            city_id: Identificador de la ciudad.

        Returns:
            True cuando fue eliminada o False cuando no existía.
        """
        ...
