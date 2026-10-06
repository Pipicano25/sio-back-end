"""Proceso `audit-outbox-worker` (`python -m sio_audit.worker`; R-11, R-12).

Entrega a Audit los eventos de la outbox del emisor: sondeo periódico, reintento
indefinido con backoff exponencial con tope, reanudación tras cualquier reinicio y
marca `SENT` solo con confirmación de Audit. La outbox en PostgreSQL es la única
fuente de recuperación.
"""

from sio_audit.worker.loop import CycleResult, Worker, run_once
from sio_audit.worker.settings import WorkerSettings

__all__ = ["CycleResult", "Worker", "WorkerSettings", "run_once"]
