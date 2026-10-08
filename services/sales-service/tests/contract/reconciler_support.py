"""Ejecución del conciliador contra la base de pruebas y los dobles (R-08)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from sales_service.application.operation_engine import OperationEngine
from sales_service.application.reconciliation_service import CycleResult, ReconciliationService
from sales_service.infrastructure.repository import SaleRepository
from sales_service.infrastructure.sequence_repository import SequenceRepository


def run_reconciler(engine, inventory, *, threshold: float = 300.0) -> CycleResult:
    with Session(engine, expire_on_commit=False) as session:
        repository = SaleRepository(session, lock_timeout_ms=5000)
        operations = OperationEngine(repository, SequenceRepository(session), inventory, clock=lambda: datetime.now(UTC))
        return ReconciliationService(repository, operations, inventory, threshold_seconds=threshold).run_once()


def age_pending(engine, seconds: int = 600) -> None:
    """Envejece las operaciones `PENDING` para que superen el umbral."""
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE sale_operations SET updated_at = now() - make_interval(secs => :s) WHERE status = 'PENDING'"),
            {"s": seconds},
        )
