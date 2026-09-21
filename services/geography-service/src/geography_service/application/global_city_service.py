from decimal import Decimal
from uuid import UUID

from geography_service.application.exceptions import (
    GlobalCityNotFoundError,
)
from geography_service.application.ports import (
    GlobalCityRepository,
)
from geography_service.domain.global_city import (
    GlobalCity,
    GlobalCityStatus,
)
from geography_service.application.pagination import (
    PageResult,
)


class GlobalCityService:
    """Implementa los casos de uso relacionados con ciudades globales."""

    def __init__(
        self,
        repository: GlobalCityRepository,
    ) -> None:
        """Inicializa el servicio.

        Args:
            repository: Repositorio utilizado para persistir ciudades.
        """
        self.repository = repository

    def list_all(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None = None,
        country_id: UUID | None = None,
        administrative_division_id: UUID | None = None,
        code: str | None = None,
        status: GlobalCityStatus | None = None,
    ) -> PageResult[GlobalCity]:
        """Obtiene ciudades utilizando paginación y filtros.

        Args:
            page: Página solicitada.
            page_size: Cantidad máxima de registros.
            search: Texto libre.
            country_id: Identificador del país.
            administrative_division_id: División administrativa.
            code: Código exacto.
            status: Estado funcional.

        Returns:
            Página filtrada de ciudades.
        """
        return self.repository.list_all(
            page=page,
            page_size=page_size,
            search=search,
            country_id=country_id,
            administrative_division_id=(
                administrative_division_id
            ),
            code=code,
            status=status,
        )

    def get_by_id(
        self,
        city_id: UUID,
    ) -> GlobalCity:
        """Obtiene una ciudad por identificador.

        Args:
            city_id: Identificador global de la ciudad.

        Returns:
            Ciudad encontrada.

        Raises:
            GlobalCityNotFoundError: Si la ciudad no existe.
        """
        city = self.repository.get_by_id(
            city_id,
        )

        if city is None:
            raise GlobalCityNotFoundError

        return city

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
        """Crea una nueva ciudad global.

        Args:
            country_id: País al que pertenece.
            administrative_division_id: División administrativa opcional.
            code: Código oficial opcional.
            name: Nombre oficial.
            latitude: Latitud aproximada.
            longitude: Longitud aproximada.
            status: Estado inicial.
            actor_id: Usuario autenticado que crea el registro.

        Returns:
            Ciudad creada.
        """
        return self.repository.create(
            country_id=country_id,
            administrative_division_id=administrative_division_id,
            code=code,
            name=name,
            latitude=latitude,
            longitude=longitude,
            status=status,
            actor_id=actor_id,
        )

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
    ) -> GlobalCity:
        """Actualiza completamente una ciudad global.

        Args:
            city_id: Identificador de la ciudad.
            expected_version: Versión conocida por el cliente.
            country_id: País al que pertenece.
            administrative_division_id: División administrativa opcional.
            code: Código oficial opcional.
            name: Nombre oficial.
            latitude: Latitud aproximada.
            longitude: Longitud aproximada.
            status: Estado funcional.
            actor_id: Usuario autenticado que modifica el registro.

        Returns:
            Ciudad actualizada.

        Raises:
            GlobalCityNotFoundError: Si la ciudad no existe.
        """
        city = self.repository.update(
            city_id,
            expected_version=expected_version,
            country_id=country_id,
            administrative_division_id=administrative_division_id,
            code=code,
            name=name,
            latitude=latitude,
            longitude=longitude,
            status=status,
            actor_id=actor_id,
        )

        if city is None:
            raise GlobalCityNotFoundError

        return city

    def delete(
        self,
        city_id: UUID,
    ) -> None:
        """Elimina una ciudad global.

        Args:
            city_id: Identificador de la ciudad.

        Raises:
            GlobalCityNotFoundError: Si la ciudad no existe.
        """
        deleted = self.repository.delete(
            city_id,
        )

        if not deleted:
            raise GlobalCityNotFoundError
