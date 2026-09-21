"""Repositorio SQLAlchemy para reglas de identificación."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from party_identity_service.application.exceptions import (
    IdentificationTypeRuleConflictError,
    IdentificationTypeRuleVersionConflictError,
)
from party_identity_service.application.identification_rules import (
    IdentificationRule,
)
from party_identity_service.application.pagination import PageResult
from party_identity_service.domain.identification_type_rule import (
    IdentificationType,
    IdentificationTypeRule,
    IdentificationSigla,
    PartyKind,
)
from party_identity_service.domain.person_identity import (
    PersonIdentificationType,
)
from party_identity_service.infrastructure.models import (
    IdentificationTypeRuleModel,
)


class SQLAlchemyIdentificationTypeRuleRepository:
    """Implementa persistencia de reglas mediante SQLAlchemy."""

    def __init__(
        self,
        session: Session,
    ) -> None:
        """Inicializa el repositorio.

        Args:
            session: Sesión SQLAlchemy activa.
        """
        self.session = session

    def list_all(
        self,
        *,
        page: int,
        page_size: int,
        party_kind: PartyKind | None = None,
        country_id: UUID | None = None,
        identification_type: IdentificationType | None = None,
        sigla: IdentificationSigla | None = None,
        is_active: bool | None = None,
    ) -> PageResult[IdentificationTypeRule]:
        """Obtiene reglas paginadas aplicando filtros."""
        conditions = []

        if party_kind is not None:
            conditions.append(
                IdentificationTypeRuleModel.party_kind == party_kind,
            )

        if country_id is not None:
            conditions.append(
                IdentificationTypeRuleModel.country_id == country_id,
            )

        if identification_type is not None:
            conditions.append(
                IdentificationTypeRuleModel.identification_type
                == identification_type,
            )

        if sigla is not None:
            conditions.append(
                IdentificationTypeRuleModel.sigla == sigla,
            )

        if is_active is not None:
            conditions.append(
                IdentificationTypeRuleModel.is_active.is_(is_active),
            )

        total_records = self.session.scalar(
            select(func.count())
            .select_from(IdentificationTypeRuleModel)
            .where(*conditions)
        ) or 0

        statement = (
            select(IdentificationTypeRuleModel)
            .where(*conditions)
            .order_by(
                IdentificationTypeRuleModel.party_kind,
                IdentificationTypeRuleModel.country_id,
                IdentificationTypeRuleModel.identification_type,
                IdentificationTypeRuleModel.valid_from.desc(),
                IdentificationTypeRuleModel.id,
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        models = self.session.scalars(
            statement,
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
        rule_id: UUID,
    ) -> IdentificationTypeRule | None:
        """Obtiene una regla por identificador."""
        model = self.session.get(
            IdentificationTypeRuleModel,
            rule_id,
        )

        if model is None:
            return None

        return self._to_domain(model)

    def create(
        self,
        *,
        party_kind: PartyKind,
        country_id: UUID,
        identification_type: IdentificationType,
        sigla: IdentificationSigla,
        number_pattern: str,
        number_pattern_description: str,
        example_value: str | None,
        min_age_years: int | None,
        max_age_years: int | None,
        is_active: bool,
        valid_from: datetime | None,
        valid_to: datetime | None,
        actor_id: str,
    ) -> IdentificationTypeRule:
        """Crea una regla de identificación."""
        actor_uuid = UUID(actor_id)
        values = {
            "party_kind": party_kind,
            "country_id": country_id,
            "identification_type": identification_type,
            "sigla": sigla,
            "number_pattern": number_pattern,
            "number_pattern_description": number_pattern_description,
            "example_value": example_value,
            "min_age_years": min_age_years,
            "max_age_years": max_age_years,
            "is_active": is_active,
            "valid_to": valid_to,
            "created_by": actor_uuid,
            "updated_by": actor_uuid,
        }

        if valid_from is not None:
            values["valid_from"] = valid_from

        model = IdentificationTypeRuleModel(
            **values,
        )

        self.session.add(model)

        try:
            self.session.commit()

        except IntegrityError:
            self.session.rollback()

            raise IdentificationTypeRuleConflictError(
                "Ya existe una regla activa para el tipo de parte, "
                "país y tipo de identificación indicados."
            ) from None

        self.session.refresh(model)

        return self._to_domain(model)

    def update(
        self,
        rule_id: UUID,
        *,
        expected_version: int,
        party_kind: PartyKind,
        country_id: UUID,
        identification_type: IdentificationType,
        sigla: IdentificationSigla,
        number_pattern: str,
        number_pattern_description: str,
        example_value: str | None,
        min_age_years: int | None,
        max_age_years: int | None,
        is_active: bool,
        valid_from: datetime | None,
        valid_to: datetime | None,
        actor_id: str,
    ) -> IdentificationTypeRule | None:
        """Actualiza completamente una regla de identificación."""
        model = self.session.get(
            IdentificationTypeRuleModel,
            rule_id,
        )

        if model is None:
            return None

        if model.version != expected_version:
            raise IdentificationTypeRuleVersionConflictError(
                "El registro fue modificado por otra operación. "
                "Consulte nuevamente antes de actualizar."
            )

        model.party_kind = party_kind
        model.country_id = country_id
        model.identification_type = identification_type
        model.sigla = sigla
        model.number_pattern = number_pattern
        model.number_pattern_description = number_pattern_description
        model.example_value = example_value
        model.min_age_years = min_age_years
        model.max_age_years = max_age_years
        model.is_active = is_active
        if valid_from is not None:
            model.valid_from = valid_from

        model.valid_to = valid_to
        model.updated_by = UUID(actor_id)

        try:
            self.session.commit()

        except IntegrityError:
            self.session.rollback()

            raise IdentificationTypeRuleConflictError(
                "Ya existe una regla activa para el tipo de parte, "
                "país y tipo de identificación indicados."
            ) from None

        except StaleDataError:
            self.session.rollback()

            raise IdentificationTypeRuleVersionConflictError(
                "El registro fue modificado por otra operación. "
                "Consulte nuevamente antes de actualizar."
            ) from None

        self.session.refresh(model)

        return self._to_domain(model)

    def get_active_rule(
        self,
        *,
        party_kind: PartyKind,
        country_id: UUID,
        identification_type: PersonIdentificationType,
    ) -> IdentificationRule | None:
        """Obtiene una regla activa y vigente.

        Args:
            party_kind: Tipo de parte que usa la regla.
            country_id: UUID externo del país.
            identification_type: Tipo de identificación.

        Returns:
            Regla activa o None cuando no existe.
        """
        now = func.now()

        statement = (
            select(IdentificationTypeRuleModel)
            .where(
                IdentificationTypeRuleModel.party_kind == party_kind,
                IdentificationTypeRuleModel.country_id == country_id,
                IdentificationTypeRuleModel.identification_type
                == identification_type,
                IdentificationTypeRuleModel.is_active.is_(True),
                IdentificationTypeRuleModel.valid_from <= now,
                or_(
                    IdentificationTypeRuleModel.valid_to.is_(None),
                    IdentificationTypeRuleModel.valid_to > now,
                ),
            )
            .order_by(
                IdentificationTypeRuleModel.valid_from.desc(),
                IdentificationTypeRuleModel.id,
            )
            .limit(1)
        )

        model = self.session.scalar(
            statement,
        )

        if model is None:
            return None

        return IdentificationRule(
            party_kind=model.party_kind,
            country_id=model.country_id,
            identification_type=model.identification_type,
            sigla=model.sigla,
            pattern=model.number_pattern,
            description=model.number_pattern_description,
            min_age_years=model.min_age_years,
            max_age_years=model.max_age_years,
        )

    def list_active_rules_by_sigla(
        self,
        *,
        party_kind: PartyKind,
        country_id: UUID,
        sigla: IdentificationSigla,
    ) -> list[IdentificationRule]:
        """Obtiene reglas activas por sigla."""
        now = func.now()

        statement = (
            select(IdentificationTypeRuleModel)
            .where(
                IdentificationTypeRuleModel.party_kind == party_kind,
                IdentificationTypeRuleModel.country_id == country_id,
                IdentificationTypeRuleModel.sigla == sigla,
                IdentificationTypeRuleModel.is_active.is_(True),
                IdentificationTypeRuleModel.valid_from <= now,
                or_(
                    IdentificationTypeRuleModel.valid_to.is_(None),
                    IdentificationTypeRuleModel.valid_to > now,
                ),
            )
            .order_by(
                IdentificationTypeRuleModel.identification_type,
                IdentificationTypeRuleModel.id,
            )
        )

        models = self.session.scalars(
            statement,
        ).all()

        return [
            IdentificationRule(
                party_kind=model.party_kind,
                country_id=model.country_id,
                identification_type=model.identification_type,
                sigla=model.sigla,
                pattern=model.number_pattern,
                description=model.number_pattern_description,
                min_age_years=model.min_age_years,
                max_age_years=model.max_age_years,
            )
            for model in models
        ]

    def has_active_rules(
        self,
        *,
        party_kind: PartyKind,
        country_id: UUID,
    ) -> bool:
        """Indica si existen reglas activas para parte y país."""
        now = func.now()

        statement = (
            select(IdentificationTypeRuleModel.id)
            .where(
                IdentificationTypeRuleModel.party_kind == party_kind,
                IdentificationTypeRuleModel.country_id == country_id,
                IdentificationTypeRuleModel.is_active.is_(True),
                IdentificationTypeRuleModel.valid_from <= now,
                or_(
                    IdentificationTypeRuleModel.valid_to.is_(None),
                    IdentificationTypeRuleModel.valid_to > now,
                ),
            )
            .limit(1)
        )

        return self.session.scalar(
            statement,
        ) is not None

    @staticmethod
    def _to_domain(
        model: IdentificationTypeRuleModel,
    ) -> IdentificationTypeRule:
        """Convierte un modelo SQLAlchemy en entidad de dominio."""
        return IdentificationTypeRule(
            id=model.id,
            party_kind=model.party_kind,
            country_id=model.country_id,
            identification_type=model.identification_type,
            sigla=model.sigla,
            number_pattern=model.number_pattern,
            number_pattern_description=model.number_pattern_description,
            example_value=model.example_value,
            min_age_years=model.min_age_years,
            max_age_years=model.max_age_years,
            is_active=model.is_active,
            valid_from=model.valid_from,
            valid_to=model.valid_to,
            version=model.version,
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
