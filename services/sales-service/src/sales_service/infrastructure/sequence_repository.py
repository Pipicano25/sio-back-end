"""Secuencias y contadores por período (FR-031 a FR-034; research.md R-03, P-02, P-04)."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from sales_service.domain.status import DOCUMENT_KIND
from sales_service.infrastructure.models import SaleSequence, SaleSequenceCounter

UQ_SEQUENCE_ACTIVE = "uq_sale_sequences_active"
UQ_SEQUENCE_SERIES = "uq_sale_sequences_series"


class SequenceRepository:
    """Secuencias y contadores por período (R-03)."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def applicable(self, company_id: UUID, branch_id: UUID) -> SaleSequence | None:
        """Secuencia activa de la sucursal o, si no hay, la de la empresa (FR-031)."""
        candidates = list(
            self.session.scalars(
                select(SaleSequence).where(
                    SaleSequence.company_id == company_id,
                    SaleSequence.document_kind == DOCUMENT_KIND,
                    SaleSequence.is_active.is_(True),
                    or_(SaleSequence.branch_id == branch_id, SaleSequence.branch_id.is_(None)),
                )
            )
        )
        for sequence in candidates:
            if sequence.branch_id == branch_id:
                return sequence
        return candidates[0] if candidates else None

    def current(self, sequence_id: UUID, period_key: str) -> int | None:
        return self.session.scalar(
            select(SaleSequenceCounter.current_number).where(
                SaleSequenceCounter.sale_sequence_id == sequence_id,
                SaleSequenceCounter.period_key == period_key,
            )
        )

    def assign(self, sequence: SaleSequence, period_key: str, actor: str) -> int:
        """Siguiente valor del contador del período en **una** sentencia (FR-032).

        El `ON CONFLICT DO UPDATE` bloquea la fila del contador hasta el `COMMIT`: los
        concurrentes del mismo período se serializan y la PK impide dos filas para un
        período nuevo. Un `ROLLBACK` no consume el número.
        """
        statement = (
            insert(SaleSequenceCounter)
            .values(
                sale_sequence_id=sequence.id,
                period_key=period_key,
                current_number=sequence.initial_number,
                created_by=actor,
                updated_by=actor,
            )
            .on_conflict_do_update(
                index_elements=[SaleSequenceCounter.sale_sequence_id, SaleSequenceCounter.period_key],
                set_={
                    "current_number": SaleSequenceCounter.current_number + 1,
                    "updated_at": func.now(),
                    "updated_by": actor,
                },
            )
            .returning(SaleSequenceCounter.current_number)
        )
        return int(self.session.execute(statement).scalar_one())

    def counters(self, sequence_id: UUID) -> list[SaleSequenceCounter]:
        return list(
            self.session.scalars(
                select(SaleSequenceCounter)
                .where(SaleSequenceCounter.sale_sequence_id == sequence_id)
                .order_by(SaleSequenceCounter.period_key)
            )
        )

    def counters_of(self, sequence_ids: Sequence[UUID]) -> dict[UUID, list[SaleSequenceCounter]]:
        result: dict[UUID, list[SaleSequenceCounter]] = {sequence_id: [] for sequence_id in sequence_ids}
        if not sequence_ids:
            return result
        for counter in self.session.scalars(
            select(SaleSequenceCounter)
            .where(SaleSequenceCounter.sale_sequence_id.in_(sequence_ids))
            .order_by(SaleSequenceCounter.sale_sequence_id, SaleSequenceCounter.period_key)
        ):
            result[counter.sale_sequence_id].append(counter)
        return result

    def get(self, company_id: UUID, sequence_id: UUID, *, lock: bool = False) -> SaleSequence | None:
        query = select(SaleSequence).where(
            SaleSequence.id == sequence_id, SaleSequence.company_id == company_id
        )
        if lock:
            query = query.with_for_update()
        return self.session.scalars(query.execution_options(populate_existing=True)).one_or_none()

    def list_for(self, company_id: UUID) -> list[SaleSequence]:
        return list(
            self.session.scalars(
                select(SaleSequence)
                .where(SaleSequence.company_id == company_id)
                .order_by(SaleSequence.created_at, SaleSequence.id)
            )
        )
