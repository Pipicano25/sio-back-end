from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from geography_service.application.exceptions import (
    GlobalCityConflictError,
    GlobalCityInvalidAdministrativeDivisionError,
    GlobalCityVersionConflictError,
)
from geography_service.domain.global_city import (
    GlobalCity,
    GlobalCityStatus,
)
from geography_service.infrastructure.models import (
    GlobalAdministrativeDivisionModel,
    GlobalCityModel,
    GlobalCountryModel,
)
from geography_service.application.pagination import (
    PageResult,
)


class SQLAlchemyGlobalCityRepository:
    """Implementa la persistencia de ciudades globales mediante SQLAlchemy."""

    def __init__(
        self,
        session: Session,
    ) -> None:
        """Inicializa el repositorio.

        Args:
            session: Sesión SQLAlchemy asociada a la request actual.
        """
        self.session = session

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
        """Obtiene ciudades globales paginadas y filtradas.

        Args:
            page: Página solicitada.
            page_size: Cantidad máxima de registros.
            search: Texto libre para nombre o código.
            country_id: País propietario.
            administrative_division_id: División administrativa asociada.
            code: Código exacto.
            status: Estado funcional.

        Returns:
            Página filtrada de ciudades globales.
        """
        conditions = []

        if search:
            pattern = f"%{search}%"

            conditions.append(
                or_(
                    GlobalCityModel.name.ilike(pattern),
                    GlobalCityModel.code.ilike(pattern),
                )
            )

        if country_id is not None:
            conditions.append(
                GlobalCityModel.country_id == country_id
            )

        if administrative_division_id is not None:
            conditions.append(
                GlobalCityModel.administrative_division_id
                == administrative_division_id
            )

        if code is not None:
            conditions.append(
                GlobalCityModel.code == code
            )

        if status is not None:
            conditions.append(
                GlobalCityModel.status == status
            )

        total_records = self.session.scalar(
            select(func.count())
            .select_from(GlobalCityModel)
            .where(*conditions)
        ) or 0

        statement = (
            select(GlobalCityModel)
            .where(*conditions)
            .order_by(
                GlobalCityModel.name,
                GlobalCityModel.id,
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        models = self.session.scalars(
            statement
        ).all()

        return PageResult(
            items=[
                self._to_domain(model)
                for model in models
            ],
            page=page,
            page_size=page_size,
            total_records=total_records,
        )

    def get_by_id(
        self,
        city_id: UUID,
    ) -> GlobalCity | None:
        """Obtiene una ciudad por identificador.

        Args:
            city_id: Identificador de la ciudad.

        Returns:
            Ciudad encontrada o None si no existe.
        """
        model = self.session.get(
            GlobalCityModel,
            city_id,
        )

        if model is None:
            return None

        return self._to_domain(model)

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
        """Crea y persiste una ciudad global.

        Args:
            country_id: País al que pertenece.
            administrative_division_id: División administrativa opcional.
            code: Código oficial opcional.
            name: Nombre oficial.
            latitude: Latitud aproximada.
            longitude: Longitud aproximada.
            status: Estado inicial.
            actor_id: Usuario que crea el registro.

        Returns:
            Ciudad creada.

        Raises:
            GlobalCityConflictError: Si el país no existe o la BD rechaza
                la operación.
            GlobalCityInvalidAdministrativeDivisionError: Si la división no
                existe o pertenece a otro país.
        """
        self._validate_country(
            country_id,
        )

        self._validate_administrative_division(
            country_id=country_id,
            administrative_division_id=administrative_division_id,
        )

        model = GlobalCityModel(
            country_id=country_id,
            administrative_division_id=administrative_division_id,
            code=code,
            name=name,
            latitude=latitude,
            longitude=longitude,
            status=status,
            created_by=actor_id,
            updated_by=actor_id,
        )

        self.session.add(
            model,
        )

        try:
            self.session.commit()

        except IntegrityError:
            self.session.rollback()

            raise GlobalCityConflictError(
                "No fue posible guardar la ciudad."
            ) from None

        self.session.refresh(
            model,
        )

        return self._to_domain(
            model,
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
    ) -> GlobalCity | None:
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
            actor_id: Usuario que realiza la modificación.

        Returns:
            Ciudad actualizada o None cuando no existe.

        Raises:
            GlobalCityVersionConflictError: Si existe un conflicto de versión.
            GlobalCityConflictError: Si la operación viola integridad.
            GlobalCityInvalidAdministrativeDivisionError: Si la división
                administrativa no corresponde al país.
        """
        model = self.session.get(
            GlobalCityModel,
            city_id,
        )

        if model is None:
            return None

        if model.version != expected_version:
            raise GlobalCityVersionConflictError(
                "El registro fue modificado por otra operación. "
                "Consulte nuevamente antes de actualizar."
            )

        self._validate_country(
            country_id,
        )

        self._validate_administrative_division(
            country_id=country_id,
            administrative_division_id=administrative_division_id,
        )

        model.country_id = country_id
        model.administrative_division_id = administrative_division_id
        model.code = code
        model.name = name
        model.latitude = latitude
        model.longitude = longitude
        model.status = status
        model.updated_by = actor_id

        try:
            self.session.commit()

        except IntegrityError:
            self.session.rollback()

            raise GlobalCityConflictError(
                "No fue posible actualizar la ciudad."
            ) from None

        except StaleDataError:
            self.session.rollback()

            raise GlobalCityVersionConflictError(
                "El registro fue modificado por otra operación. "
                "Consulte nuevamente antes de actualizar."
            ) from None

        self.session.refresh(
            model,
        )

        return self._to_domain(
            model,
        )

    def delete(
        self,
        city_id: UUID,
    ) -> bool:
        """Elimina físicamente una ciudad.

        Args:
            city_id: Identificador de la ciudad.

        Returns:
            True si fue eliminada o False si no existía.

        Raises:
            GlobalCityConflictError: Si existen referencias que impiden
                eliminarla.
            GlobalCityVersionConflictError: Si ocurre un conflicto concurrente.
        """
        model = self.session.get(
            GlobalCityModel,
            city_id,
        )

        if model is None:
            return False

        self.session.delete(
            model,
        )

        try:
            self.session.commit()

        except IntegrityError:
            self.session.rollback()

            raise GlobalCityConflictError(
                "No se puede eliminar la ciudad porque "
                "existen registros relacionados."
            ) from None

        except StaleDataError:
            self.session.rollback()

            raise GlobalCityVersionConflictError(
                "El registro fue modificado por otra operación."
            ) from None

        return True

    def _validate_country(
        self,
        country_id: UUID,
    ) -> None:
        """Valida que el país indicado exista.

        Args:
            country_id: Identificador del país.

        Raises:
            GlobalCityConflictError: Si el país no existe.
        """
        country = self.session.get(
            GlobalCountryModel,
            country_id,
        )

        if country is None:
            raise GlobalCityConflictError(
                "El país indicado no existe."
            )

    def _validate_administrative_division(
        self,
        *,
        country_id: UUID,
        administrative_division_id: UUID | None,
    ) -> None:
        """Valida la división administrativa opcional de una ciudad.

        Args:
            country_id: País asignado a la ciudad.
            administrative_division_id: División administrativa indicada.

        Raises:
            GlobalCityInvalidAdministrativeDivisionError: Si la división no
                existe o pertenece a un país diferente.
        """
        if administrative_division_id is None:
            return

        division = self.session.get(
            GlobalAdministrativeDivisionModel,
            administrative_division_id,
        )

        if division is None:
            raise GlobalCityInvalidAdministrativeDivisionError(
                "La división administrativa indicada no existe."
            )

        if division.country_id != country_id:
            raise GlobalCityInvalidAdministrativeDivisionError(
                "La división administrativa debe pertenecer "
                "al mismo país de la ciudad."
            )

    @staticmethod
    def _to_domain(
        model: GlobalCityModel,
    ) -> GlobalCity:
        """Convierte un modelo SQLAlchemy en una entidad de dominio.

        Args:
            model: Modelo persistente de la ciudad.

        Returns:
            Entidad de dominio equivalente.
        """
        return GlobalCity(
            id=model.id,
            country_id=model.country_id,
            administrative_division_id=model.administrative_division_id,
            code=model.code,
            name=model.name,
            latitude=model.latitude,
            longitude=model.longitude,
            status=model.status,
            version=model.version,
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
