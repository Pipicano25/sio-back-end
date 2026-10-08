"""Secuencias de numeración (Historia 5; FR-031 a FR-034, P-02, P-04; research.md R-03).

- A lo sumo una secuencia activa por empresa, sucursal (o ninguna) y tipo documental:
  activar otra en el mismo alcance → `409 SEQUENCE_ALREADY_ACTIVE`.
- Tras el primer número asignado (existe algún contador) son inmutables `prefix`,
  `separator`, `number_length`, `series_code`, `reset_policy`, `initial_number`,
  `branch_id` y `document_kind` → `409 SEQUENCE_IN_USE`. `maximum_number` puede cambiar
  si no queda por debajo de ningún contador. Los contadores no se escriben por la API.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError

from sales_service.application import audit_events as audit
from sales_service.application.branch_access import require_membership
from sales_service.application.exceptions import (
    NotFoundError,
    ReferencesNotEligibleError,
    SequenceAlreadyActiveError,
    SequenceInUseError,
    ValidationFailedError,
    VersionConflictError,
    field_error,
)
from sales_service.application.ports import OperationalContextDirectory
from sales_service.application.sale_service import Actor
from sales_service.application.snapshots import touch
from sales_service.domain.status import DOCUMENT_KIND
from sales_service.infrastructure.models import SaleSequence, SaleSequenceCounter
from sales_service.infrastructure.repository import SaleRepository, violated_constraint
from sales_service.infrastructure.sequence_repository import UQ_SEQUENCE_ACTIVE, UQ_SEQUENCE_SERIES, SequenceRepository

IMMUTABLE_AFTER_USE = (
    "branch_id",
    "series_code",
    "prefix",
    "separator",
    "initial_number",
    "number_length",
    "reset_policy",
)


@dataclass(frozen=True, slots=True)
class SequenceData:
    branch_id: UUID | None
    series_code: str
    prefix: str
    separator: str
    initial_number: int
    maximum_number: int | None
    number_length: int
    reset_policy: str


@dataclass(frozen=True, slots=True)
class SequenceView:
    sequence: SaleSequence
    counters: list[SaleSequenceCounter]


def sequence_values(sequence: SaleSequence) -> dict:
    return {
        "branch_id": sequence.branch_id,
        "document_kind": sequence.document_kind,
        "series_code": sequence.series_code,
        "prefix": sequence.prefix,
        "separator": sequence.separator,
        "initial_number": sequence.initial_number,
        "maximum_number": sequence.maximum_number,
        "number_length": sequence.number_length,
        "reset_policy": sequence.reset_policy,
        "is_active": sequence.is_active,
        "version": sequence.version,
    }


class SequenceService:
    def __init__(
        self,
        repository: SaleRepository,
        sequences: SequenceRepository,
        operational_context: OperationalContextDirectory,
        *,
        clock: Callable[[], datetime],
    ) -> None:
        self._repo = repository
        self._sequences = sequences
        self._oc = operational_context
        self._clock = clock

    def _check_branch(self, company_id: UUID, branch_id: UUID | None) -> None:
        if branch_id is None:
            return
        branch = self._oc.get_branch(branch_id)
        if branch is None or branch.company_id != company_id:
            raise ValidationFailedError([field_error("branch_id", "BRANCH_NOT_FOUND", "La sucursal no existe en la empresa.")])
        if branch.status != "ACTIVE":
            raise ReferencesNotEligibleError([field_error("branch_id", "BRANCH_INACTIVE", "La sucursal no está activa.")])

    def _translate(self, error: IntegrityError):
        constraint = violated_constraint(error)
        if constraint == UQ_SEQUENCE_ACTIVE:
            return SequenceAlreadyActiveError()
        if constraint == UQ_SEQUENCE_SERIES:
            return SequenceInUseError(["series_code"])
        return None

    def _audit(self, action: str, sequence: SaleSequence, application_user_id, previous=None) -> None:
        audit.record(
            self._repo.session,
            action=action,
            entity_type=audit.SEQUENCE,
            entity_id=sequence.id,
            company_id=sequence.company_id,
            branch_id=sequence.branch_id,
            application_user_id=application_user_id,
            previous_values=previous,
            new_values=sequence_values(sequence),
        )

    def create(self, company_id: UUID, data: SequenceData, actor: Actor) -> SequenceView:
        access = require_membership(actor.access, company_id)
        self._check_branch(company_id, data.branch_id)
        now = self._clock()
        sequence = SaleSequence(
            id=uuid4(),
            company_id=company_id,
            branch_id=data.branch_id,
            document_kind=DOCUMENT_KIND,
            series_code=data.series_code,
            prefix=data.prefix,
            separator=data.separator,
            initial_number=data.initial_number,
            maximum_number=data.maximum_number,
            number_length=data.number_length,
            reset_policy=data.reset_policy,
            is_active=True,
            created_at=now,
            updated_at=now,
            created_by=actor.subject,
            updated_by=actor.subject,
        )
        try:
            self._repo.begin()
            self._repo.add(sequence)
            self._repo.flush()
            self._audit(audit.CREATE_SEQUENCE, sequence, access.application_user_id)
            self._repo.commit()
        except IntegrityError as error:
            self._repo.rollback()
            translated = self._translate(error)
            if translated is not None:
                raise translated from None
            raise
        except Exception:
            self._repo.rollback()
            raise
        return SequenceView(sequence, [])

    def _locked(self, company_id: UUID, sequence_id: UUID, version: int) -> SaleSequence:
        self._repo.begin()
        sequence = self._sequences.get(company_id, sequence_id, lock=True)
        if sequence is None:
            raise NotFoundError()
        if sequence.version != version:
            raise VersionConflictError()
        return sequence

    def update(self, company_id: UUID, sequence_id: UUID, data: SequenceData, version: int, actor: Actor) -> SequenceView:
        access = require_membership(actor.access, company_id)
        if self._sequences.get(company_id, sequence_id) is None:
            raise NotFoundError()
        self._repo.end_read()
        self._check_branch(company_id, data.branch_id)
        try:
            sequence = self._locked(company_id, sequence_id, version)
            previous = sequence_values(sequence)
            counters = self._sequences.counters(sequence.id)
            if counters:
                changed = [name for name in IMMUTABLE_AFTER_USE if getattr(sequence, name) != getattr(data, name)]
                if changed:
                    raise SequenceInUseError(changed)
                highest = max(counter.current_number for counter in counters)
                if data.maximum_number is not None and data.maximum_number < highest:
                    raise ValidationFailedError(
                        [
                            field_error(
                                "maximum_number",
                                "MAXIMUM_NUMBER_BELOW_CURRENT",
                                f"El máximo no puede ser menor que el último número asignado ({highest}).",
                            )
                        ]
                    )
            for name in IMMUTABLE_AFTER_USE:
                setattr(sequence, name, getattr(data, name))
            sequence.maximum_number = data.maximum_number
            touch(sequence, actor.subject, self._clock())
            self._repo.flush()
            self._audit(audit.UPDATE_SEQUENCE, sequence, access.application_user_id, previous)
            self._repo.commit()
            return SequenceView(sequence, counters)
        except IntegrityError as error:
            self._repo.rollback()
            translated = self._translate(error)
            if translated is not None:
                raise translated from None
            raise
        except Exception:
            self._repo.rollback()
            raise

    def set_active(self, company_id: UUID, sequence_id: UUID, active: bool, version: int, actor: Actor) -> SequenceView:
        access = require_membership(actor.access, company_id)
        try:
            sequence = self._locked(company_id, sequence_id, version)
            previous = sequence_values(sequence)
            sequence.is_active = active
            touch(sequence, actor.subject, self._clock())
            self._repo.flush()
            self._audit(
                audit.REACTIVATE_SEQUENCE if active else audit.DEACTIVATE_SEQUENCE,
                sequence,
                access.application_user_id,
                previous,
            )
            self._repo.commit()
            return SequenceView(sequence, self._sequences.counters(sequence.id))
        except IntegrityError as error:
            self._repo.rollback()
            translated = self._translate(error)
            if translated is not None:
                raise translated from None
            raise
        except Exception:
            self._repo.rollback()
            raise

    def get(self, company_id: UUID, sequence_id: UUID, actor: Actor) -> SequenceView:
        require_membership(actor.access, company_id)
        sequence = self._sequences.get(company_id, sequence_id)
        if sequence is None:
            raise NotFoundError()
        return SequenceView(sequence, self._sequences.counters(sequence.id))

    def list(self, company_id: UUID, actor: Actor) -> list[SequenceView]:
        require_membership(actor.access, company_id)
        sequences = self._sequences.list_for(company_id)
        counters = self._sequences.counters_of([sequence.id for sequence in sequences])
        return [SequenceView(sequence, counters[sequence.id]) for sequence in sequences]
