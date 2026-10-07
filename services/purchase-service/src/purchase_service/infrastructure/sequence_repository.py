"""Secuencias y contadores por período (FR-031 a FR-034; research.md R-03, P-02, P-04)."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from purchase_service.domain.status import DOCUMENT_KIND
from purchase_service.infrastructure.models import PurchaseSequence, PurchaseSequenceCounter

UQ_SEQUENCE_ACTIVE = "uq_purchase_sequences_active"
UQ_SEQUENCE_SERIES = "uq_purchase_sequences_series"


class SequenceRepository:
    """Secuencias y contadores por período (R-03)."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def applicable(self, company_id: UUID, branch_id: UUID) -> PurchaseSequence | None:
        """Secuencia activa de la sucursal o, si no hay, la de la empresa (FR-031)."""
        candidates = list(
            self.session.scalars(
                select(PurchaseSequence).where(
                    PurchaseSequence.company_id == company_id,
                    PurchaseSequence.document_kind == DOCUMENT_KIND,
                    PurchaseSequence.is_active.is_(True),
                    or_(PurchaseSequence.branch_id == branch_id, PurchaseSequence.branch_id.is_(None)),
                )
            )
        )
        for sequence in candidates:
            if sequence.branch_id == branch_id:
                return sequence
        return candidates[0] if candidates else None

    def current(self, sequence_id: UUID, period_key: str) -> int | None:
        return self.session.scalar(
            select(PurchaseSequenceCounter.current_number).where(
                PurchaseSequenceCounter.purchase_sequence_id == sequence_id,
                PurchaseSequenceCounter.period_key == period_key,
            )
        )

    def assign(self, sequence: PurchaseSequence, period_key: str, actor: str) -> int:
        """Siguiente valor del contador del período en **una** sentencia (FR-032).

        El `ON CONFLICT DO UPDATE` bloquea la fila del contador hasta el `COMMIT`: los
        concurrentes del mismo período se serializan y la PK impide dos filas para un
        período nuevo. Un `ROLLBACK` no consume el número.
        """
        statement = (
            insert(PurchaseSequenceCounter)
            .values(
                purchase_sequence_id=sequence.id,
                period_key=period_key,
                current_number=sequence.initial_number,
                created_by=actor,
                updated_by=actor,
            )
            .on_conflict_do_update(
                index_elements=[PurchaseSequenceCounter.purchase_sequence_id, PurchaseSequenceCounter.period_key],
                set_={
                    "current_number": PurchaseSequenceCounter.current_number + 1,
                    "updated_at": func.now(),
                    "updated_by": actor,
                },
            )
            .returning(PurchaseSequenceCounter.current_number)
        )
        return int(self.session.execute(statement).scalar_one())

    def counters(self, sequence_id: UUID) -> list[PurchaseSequenceCounter]:
        return list(
            self.session.scalars(
                select(PurchaseSequenceCounter)
                .where(PurchaseSequenceCounter.purchase_sequence_id == sequence_id)
                .order_by(PurchaseSequenceCounter.period_key)
            )
        )

    def counters_of(self, sequence_ids: Sequence[UUID]) -> dict[UUID, list[PurchaseSequenceCounter]]:
        result: dict[UUID, list[PurchaseSequenceCounter]] = {sequence_id: [] for sequence_id in sequence_ids}
        if not sequence_ids:
            return result
        for counter in self.session.scalars(
            select(PurchaseSequenceCounter)
            .where(PurchaseSequenceCounter.purchase_sequence_id.in_(sequence_ids))
            .order_by(PurchaseSequenceCounter.purchase_sequence_id, PurchaseSequenceCounter.period_key)
        ):
            result[counter.purchase_sequence_id].append(counter)
        return result

    def get(self, company_id: UUID, sequence_id: UUID, *, lock: bool = False) -> PurchaseSequence | None:
        query = select(PurchaseSequence).where(
            PurchaseSequence.id == sequence_id, PurchaseSequence.company_id == company_id
        )
        if lock:
            query = query.with_for_update()
        return self.session.scalars(query.execution_options(populate_existing=True)).one_or_none()

    def list_for(self, company_id: UUID) -> list[PurchaseSequence]:
        return list(
            self.session.scalars(
                select(PurchaseSequence)
                .where(PurchaseSequence.company_id == company_id)
                .order_by(PurchaseSequence.created_at, PurchaseSequence.id)
            )
        )
