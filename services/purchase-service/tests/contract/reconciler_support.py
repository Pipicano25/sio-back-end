"""Ejecución del conciliador contra la base de pruebas y los dobles (R-08)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from purchase_service.application.operation_engine import OperationEngine
from purchase_service.application.reconciliation_service import CycleResult, ReconciliationService
from purchase_service.infrastructure.repository import PurchaseRepository


def run_reconciler(engine, inventory, *, threshold: float = 300.0) -> CycleResult:
    with Session(engine, expire_on_commit=False) as session:
        repository = PurchaseRepository(session, lock_timeout_ms=5000)
        operations = OperationEngine(repository, inventory, clock=lambda: datetime.now(UTC))
        return ReconciliationService(repository, operations, inventory, threshold_seconds=threshold).run_once()


def age_pending(engine, seconds: int = 600) -> None:
    """Envejece las operaciones `PENDING` para que superen el umbral."""
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE purchase_operations SET updated_at = now() - make_interval(secs => :s) WHERE status = 'PENDING'"),
            {"s": seconds},
        )
