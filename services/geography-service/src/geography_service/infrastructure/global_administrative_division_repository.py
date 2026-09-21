from uuid import UUID

from sqlalchemy import select, func,  or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from geography_service.application.exceptions import (
    GlobalAdministrativeDivisionConflictError,
    GlobalAdministrativeDivisionInvalidParentError,
    GlobalAdministrativeDivisionVersionConflictError,
)
from geography_service.domain.global_administrative_division import (
    AdministrativeDivisionStatus,
    AdministrativeDivisionType,
    GlobalAdministrativeDivision,
)
from geography_service.infrastructure.models import (
    GlobalAdministrativeDivisionModel,
    GlobalCountryModel,
)
from geography_service.application.pagination import (
    PageResult,
)


class SQLAlchemyGlobalAdministrativeDivisionRepository:
    def __init__(
        self,
        session: Session,
    ) -> None:
        self.session = session

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
        """Obtiene divisiones administrativas paginadas y filtradas.

        Args:
            page: Página solicitada.
            page_size: Cantidad máxima de registros.
            search: Texto libre para código o nombre.
            country_id: País propietario.
            parent_division_id: División superior.
            division_type: Tipo administrativo.
            status: Estado funcional.

        Returns:
            Página filtrada de divisiones administrativas.
        """
        conditions = []

        if search:
            pattern = f"%{search}%"

            conditions.append(
                or_(
                    GlobalAdministrativeDivisionModel.name.ilike(
                        pattern
                    ),
                    GlobalAdministrativeDivisionModel.code.ilike(
                        pattern
                    ),
                )
            )

        if country_id is not None:
            conditions.append(
                GlobalAdministrativeDivisionModel.country_id
                == country_id
            )

        if parent_division_id is not None:
            conditions.append(
                GlobalAdministrativeDivisionModel.parent_division_id
                == parent_division_id
            )

        if division_type is not None:
            conditions.append(
                GlobalAdministrativeDivisionModel.division_type
                == division_type
            )

        if status is not None:
            conditions.append(
                GlobalAdministrativeDivisionModel.status
                == status
            )

        total_records = self.session.scalar(
            select(func.count())
            .select_from(
                GlobalAdministrativeDivisionModel
            )
            .where(*conditions)
        ) or 0

        statement = (
            select(
                GlobalAdministrativeDivisionModel
            )
            .where(*conditions)
            .order_by(
                GlobalAdministrativeDivisionModel.name,
                GlobalAdministrativeDivisionModel.id,
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
        division_id: UUID,
    ) -> GlobalAdministrativeDivision | None:
        model = self.session.get(
            GlobalAdministrativeDivisionModel,
            division_id,
        )

        if model is None:
            return None

        return self._to_domain(model)

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
        self._validate_country(country_id)

        self._validate_parent(
            country_id=country_id,
            parent_division_id=parent_division_id,
        )

        model = GlobalAdministrativeDivisionModel(
            country_id=country_id,
            parent_division_id=parent_division_id,
            code=code,
            name=name,
            division_type=division_type,
            status=status,
            created_by=actor_id,
            updated_by=actor_id,
        )

        self.session.add(model)

        try:
            self.session.commit()

        except IntegrityError:
            self.session.rollback()

            raise GlobalAdministrativeDivisionConflictError(
                "No fue posible guardar la división administrativa."
            ) from None

        self.session.refresh(model)

        return self._to_domain(model)

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
        model = self.session.get(
            GlobalAdministrativeDivisionModel,
            division_id,
        )

        if model is None:
            return None

        if model.version != expected_version:
            raise GlobalAdministrativeDivisionVersionConflictError(
                "El registro fue modificado por otra operación. "
                "Consulte nuevamente antes de actualizar."
            )

        if parent_division_id == division_id:
            raise GlobalAdministrativeDivisionInvalidParentError(
                "Una división administrativa no puede ser su propia división superior."
            )

        self._validate_country(country_id)

        self._validate_parent(
            country_id=country_id,
            parent_division_id=parent_division_id,
        )

        model.country_id = country_id
        model.parent_division_id = parent_division_id
        model.code = code
        model.name = name
        model.division_type = division_type
        model.status = status
        model.updated_by = actor_id

        try:
            self.session.commit()

        except IntegrityError:
            self.session.rollback()

            raise GlobalAdministrativeDivisionConflictError(
                "No fue posible actualizar la división administrativa."
            ) from None

        except StaleDataError:
            self.session.rollback()

            raise GlobalAdministrativeDivisionVersionConflictError(
                "El registro fue modificado por otra operación. "
                "Consulte nuevamente antes de actualizar."
            ) from None

        self.session.refresh(model)

        return self._to_domain(model)

    def delete(
        self,
        division_id: UUID,
    ) -> bool:
        model = self.session.get(
            GlobalAdministrativeDivisionModel,
            division_id,
        )

        if model is None:
            return False

        self.session.delete(model)

        try:
            self.session.commit()

        except IntegrityError:
            self.session.rollback()

            raise GlobalAdministrativeDivisionConflictError(
                "No se puede eliminar la división porque "
                "existen registros relacionados."
            ) from None

        return True

    def _validate_country(
        self,
        country_id: UUID,
    ) -> None:
        country = self.session.get(
            GlobalCountryModel,
            country_id,
        )

        if country is None:
            raise GlobalAdministrativeDivisionConflictError(
                "El país indicado no existe."
            )

    def _validate_parent(
        self,
        *,
        country_id: UUID,
        parent_division_id: UUID | None,
    ) -> None:
        if parent_division_id is None:
            return

        parent = self.session.get(
            GlobalAdministrativeDivisionModel,
            parent_division_id,
        )

        if parent is None:
            raise GlobalAdministrativeDivisionInvalidParentError(
                "La división administrativa superior indicada no existe."
            )

        if parent.country_id != country_id:
            raise GlobalAdministrativeDivisionInvalidParentError(
                "La división superior debe pertenecer al mismo país."
            )

    @staticmethod
    def _to_domain(
        model: GlobalAdministrativeDivisionModel,
    ) -> GlobalAdministrativeDivision:
        return GlobalAdministrativeDivision(
            id=model.id,
            country_id=model.country_id,
            parent_division_id=model.parent_division_id,
            code=model.code,
            name=model.name,
            division_type=model.division_type,
            status=model.status,
            version=model.version,
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )