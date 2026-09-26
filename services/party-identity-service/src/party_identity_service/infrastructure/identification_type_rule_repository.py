"""Repositorio SQLAlchemy para reglas de identificación."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from party_identity_service.application.exceptions import (
    DuplicateActiveRuleError,
    InvalidStatusTransitionError,
)
from party_identity_service.application.identification_rules import (
    IdentificationRule,
)
from party_identity_service.application.pagination import PageResult
from party_identity_service.domain.identification_type_rule import (
    IdentificationSigla,
    IdentificationType,
    IdentificationTypeRule,
    PartyKind,
)
from party_identity_service.infrastructure.models import (
    IdentificationTypeRuleModel,
)
from party_identity_service.infrastructure.persistence import (
    commit_or_translate,
    load_for_update,
)

ACTIVE_RULE_CONSTRAINT = "uq_identification_type_rules_active"
DUPLICATES = {ACTIVE_RULE_CONSTRAINT: DuplicateActiveRuleError}
NOT_FOUND_MESSAGE = "La regla solicitada no existe."


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
        valid_from: datetime | None,
        valid_to: datetime | None,
        actor_id: str,
    ) -> IdentificationTypeRule:
        """Crea una regla activa."""
        values: dict[str, Any] = {
            "party_kind": party_kind,
            "country_id": country_id,
            "identification_type": identification_type,
            "sigla": sigla,
            "number_pattern": number_pattern,
            "number_pattern_description": number_pattern_description,
            "example_value": example_value,
            "min_age_years": min_age_years,
            "max_age_years": max_age_years,
            "is_active": True,
            "valid_to": valid_to,
            "created_by": actor_id,
            "updated_by": actor_id,
        }

        if valid_from is not None:
            values["valid_from"] = valid_from

        model = IdentificationTypeRuleModel(
            **values,
        )

        self.session.add(model)
        commit_or_translate(
            self.session,
            duplicates=DUPLICATES,
        )
        self.session.refresh(model)

        return self._to_domain(model)

    def update(
        self,
        rule_id: UUID,
        *,
        expected_version: int,
        values: dict[str, Any],
        actor_id: str,
    ) -> IdentificationTypeRule:
        """Modifica en sitio los campos indicados con control de versión."""
        model = load_for_update(
            self.session,
            IdentificationTypeRuleModel,
            rule_id,
            expected_version=expected_version,
            not_found_message=NOT_FOUND_MESSAGE,
        )

        for field, value in values.items():
            setattr(model, field, value)

        model.updated_by = actor_id
        commit_or_translate(
            self.session,
            duplicates=DUPLICATES,
        )
        self.session.refresh(model)

        return self._to_domain(model)

    def create_version(
        self,
        rule_id: UUID,
        *,
        expected_version: int,
        number_pattern: str,
        number_pattern_description: str,
        example_value: str | None,
        min_age_years: int | None,
        max_age_years: int | None,
        actor_id: str,
    ) -> IdentificationTypeRule:
        """Cierra la regla vigente y crea su sucesora en una transacción (R-09).

        La regla actual se bloquea (`SELECT ... FOR UPDATE`); si la inserción
        falla, la transacción se revierte y la regla actual queda intacta.
        """
        current = self._lock_active(
            rule_id,
            expected_version=expected_version,
        )
        self._close(current, actor_id=actor_id)
        # Se escribe el cierre antes de insertar la sucesora para no violar el
        # índice único parcial de reglas activas.
        self.session.flush()

        successor = IdentificationTypeRuleModel(
            party_kind=current.party_kind,
            country_id=current.country_id,
            identification_type=current.identification_type,
            sigla=current.sigla,
            number_pattern=number_pattern,
            number_pattern_description=number_pattern_description,
            example_value=example_value,
            min_age_years=min_age_years,
            max_age_years=max_age_years,
            is_active=True,
            created_by=actor_id,
            updated_by=actor_id,
        )
        self.session.add(successor)
        commit_or_translate(
            self.session,
            duplicates=DUPLICATES,
        )
        self.session.refresh(successor)

        return self._to_domain(successor)

    def deactivate(
        self,
        rule_id: UUID,
        *,
        expected_version: int,
        actor_id: str,
    ) -> IdentificationTypeRule:
        """Retira una regla: `is_active = FALSE` y `valid_to` si no había uno anterior."""
        model = self._lock_active(
            rule_id,
            expected_version=expected_version,
        )
        self._close(model, actor_id=actor_id)
        commit_or_translate(
            self.session,
            duplicates=DUPLICATES,
        )
        self.session.refresh(model)

        return self._to_domain(model)

    def list_active_rules_by_sigla(
        self,
        *,
        party_kind: PartyKind,
        country_id: UUID,
        sigla: IdentificationSigla,
    ) -> list[IdentificationRule]:
        """Obtiene reglas activas y vigentes por sigla (FR-015)."""
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

    def _lock_active(
        self,
        rule_id: UUID,
        *,
        expected_version: int,
    ) -> IdentificationTypeRuleModel:
        model = load_for_update(
            self.session,
            IdentificationTypeRuleModel,
            rule_id,
            expected_version=expected_version,
            not_found_message=NOT_FOUND_MESSAGE,
        )

        if not model.is_active:
            self.session.rollback()
            raise InvalidStatusTransitionError(
                "Una regla histórica no admite cambios."
            )

        return model

    def _close(
        self,
        model: IdentificationTypeRuleModel,
        *,
        actor_id: str,
    ) -> None:
        """Deja la regla histórica fijando `valid_to` al momento actual.

        Solo se adelanta `valid_to` si la regla ya entró en vigencia y no tenía
        un fin anterior; una regla programada a futuro se inactiva sin fin de
        vigencia para respetar `valid_to > valid_from`.
        """
        now = self.session.scalar(select(func.now()))
        model.is_active = False
        model.updated_by = actor_id

        if model.valid_from <= now and (model.valid_to is None or model.valid_to > now):
            model.valid_to = now

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
