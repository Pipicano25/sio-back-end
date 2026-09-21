from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from geography_service.application.exceptions import (
    GlobalCountryConflictError,
    GlobalCountryVersionConflictError,
)
from geography_service.domain.global_country import (
    GlobalCountry,
    GlobalCountryStatus,
)
from geography_service.infrastructure.models import (
    GlobalCountryModel,
)
from geography_service.application.pagination import (
    PageResult,
)


class SQLAlchemyGlobalCountryRepository:
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
        iso2_code: str | None = None,
        iso3_code: str | None = None,
        status: GlobalCountryStatus | None = None,
    ) -> PageResult[GlobalCountry]:
        """Obtiene países paginados aplicando búsqueda y filtros.

        Args:
            page: Página solicitada.
            page_size: Cantidad máxima de registros.
            search: Texto libre para nombre o códigos ISO.
            iso2_code: Código ISO2 exacto.
            iso3_code: Código ISO3 exacto.
            status: Estado funcional exacto.

        Returns:
            Página filtrada de países globales.
        """
        conditions = []

        if search:
            pattern = f"%{search}%"

            conditions.append(
                or_(
                    GlobalCountryModel.name.ilike(pattern),
                    GlobalCountryModel.iso2_code.ilike(pattern),
                    GlobalCountryModel.iso3_code.ilike(pattern),
                )
            )

        if iso2_code:
            conditions.append(
                GlobalCountryModel.iso2_code == iso2_code
            )

        if iso3_code:
            conditions.append(
                GlobalCountryModel.iso3_code == iso3_code
            )

        if status:
            conditions.append(
                GlobalCountryModel.status == status
            )

        total_records = self.session.scalar(
            select(func.count())
            .select_from(GlobalCountryModel)
            .where(*conditions)
        ) or 0

        statement = (
            select(GlobalCountryModel)
            .where(*conditions)
            .order_by(
                GlobalCountryModel.name,
                GlobalCountryModel.id,
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
        country_id: UUID,
    ) -> GlobalCountry | None:
        model = self.session.get(
            GlobalCountryModel,
            country_id,
        )

        if model is None:
            return None

        return self._to_domain(model)

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
        model = GlobalCountryModel(
            iso2_code=iso2_code,
            iso3_code=iso3_code,
            name=name,
            phone_prefix=phone_prefix,
            status=status,
            created_by=actor_id,
            updated_by=actor_id,
        )

        self.session.add(model)

        try:
            self.session.commit()

        except IntegrityError:
            self.session.rollback()

            raise GlobalCountryConflictError(
                "Ya existe un país con alguno de "
                "los códigos ISO indicados."
            ) from None

        self.session.refresh(model)

        return self._to_domain(model)

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
        model = self.session.get(
            GlobalCountryModel,
            country_id,
        )

        if model is None:
            return None

        if model.version != expected_version:
            raise GlobalCountryVersionConflictError(
                "El registro fue modificado por otra operación. "
                "Consulte nuevamente antes de actualizar."
            )

        model.iso2_code = iso2_code
        model.iso3_code = iso3_code
        model.name = name
        model.phone_prefix = phone_prefix
        model.status = status
        model.updated_by = actor_id

        try:
            self.session.commit()

        except IntegrityError:
            self.session.rollback()

            raise GlobalCountryConflictError(
                "Ya existe un país con alguno de "
                "los códigos ISO indicados."
            ) from None

        except StaleDataError:
            self.session.rollback()

            raise GlobalCountryVersionConflictError(
                "El registro fue modificado por otra operación. "
                "Consulte nuevamente antes de actualizar."
            ) from None

        self.session.refresh(model)

        return self._to_domain(model)

    def delete(
        self,
        country_id: UUID,
    ) -> bool:
        model = self.session.get(
            GlobalCountryModel,
            country_id,
        )

        if model is None:
            return False

        self.session.delete(
            model,
        )

        try:
            self.session.commit()

        except StaleDataError:
            self.session.rollback()

            raise GlobalCountryVersionConflictError(
                "El registro fue modificado por otra operación."
            ) from None

        return True

    @staticmethod
    def _to_domain(
        model: GlobalCountryModel,
    ) -> GlobalCountry:
        return GlobalCountry(
            id=model.id,
            iso2_code=model.iso2_code,
            iso3_code=model.iso3_code,
            name=model.name,
            phone_prefix=model.phone_prefix,
            status=model.status,
            version=model.version,
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )