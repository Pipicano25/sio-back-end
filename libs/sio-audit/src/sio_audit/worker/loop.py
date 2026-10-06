"""Bucle de entrega de la outbox de auditoría (R-11; FR-075, FR-077).

Cada ciclo, en una transacción:

1. toma hasta `batch_size` eventos `PENDING` vencidos con `FOR UPDATE SKIP LOCKED`
   (varias réplicas no envían la misma fila);
2. los envía a `POST {AUDIT}/audit-events/batch`;
3. confirmación (`CREATED` / `ALREADY_EXISTS`) → `SENT` con `sent_at`;
4. `409` / `422` del lote → los eventos señalados se reprograman con el backoff
   máximo (rechazo permanente, quedan en logs con `event_id` y `code`) y el resto
   se reenvía en el mismo ciclo;
5. `503`, `408`, `429`, otros `5xx`, red, tiempo agotado o token no obtenido →
   todos se reprograman con backoff exponencial (`initial * factor^(attempts-1)`,
   tope `max`, jitter ±10 %);
6. `401` → se renueva el token una vez; si persiste, rechazo permanente igual que `403`.

Nunca marca `SENT` sin confirmación y nunca borra filas. Los logs nunca incluyen
`previous_values`, `new_values` ni el token.
"""

from __future__ import annotations

import logging
import random
import re
import threading
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine

from sio_audit.worker.settings import WorkerSettings
from sio_audit.worker.token import ClientCredentialsToken, TokenUnavailableError

logger = logging.getLogger("sio_audit")

RETRYABLE_STATUSES = frozenset({408, 429})
_EVENT_INDEX = re.compile(r"^events\[(\d+)\]")


@dataclass(frozen=True, slots=True)
class PendingEvent:
    event_id: str
    payload: dict[str, Any]
    attempts: int


@dataclass(slots=True)
class CycleResult:
    """Resumen de un ciclo (para pruebas y logs)."""

    selected: int = 0
    sent: list[str] = field(default_factory=list)
    rejected: list[str] = field(default_factory=list)
    retried: list[str] = field(default_factory=list)


def backoff_seconds(
    attempts: int,
    settings: WorkerSettings,
    *,
    maximum: bool = False,
    rng: Callable[[float, float], float] = random.uniform,
) -> float:
    """Espera antes del próximo intento (attempts ≥ 1 es el número de intentos ya hechos)."""
    if maximum:
        base = settings.backoff_max_seconds
    else:
        exponent = max(attempts - 1, 0)
        base = min(
            settings.backoff_max_seconds,
            settings.backoff_initial_seconds * settings.backoff_factor**exponent,
        )
    return min(settings.backoff_max_seconds, base * rng(0.9, 1.1))


class AuditClient:
    """Cliente HTTP hacia Audit con el token técnico del emisor."""

    def __init__(
        self,
        settings: WorkerSettings,
        *,
        transport: httpx.BaseTransport | None = None,
        token: ClientCredentialsToken | None = None,
    ) -> None:
        self._url = f"{settings.audit_base_url}/audit-events/batch"
        self._timeout = settings.http_timeout_seconds
        self._transport = transport
        self._token = token or ClientCredentialsToken(
            token_url=settings.token_url,
            client_id=settings.client_id,
            client_secret=settings.client_secret,
            timeout_seconds=settings.http_timeout_seconds,
            transport=transport,
        )

    def send_batch(self, payloads: Sequence[dict[str, Any]]) -> httpx.Response:
        """Envía el lote; ante `401` renueva el token una vez."""
        response = self._post(payloads)

        if response.status_code == 401:
            self._token.invalidate()
            response = self._post(payloads)

        return response

    def _post(self, payloads: Sequence[dict[str, Any]]) -> httpx.Response:
        with httpx.Client(timeout=self._timeout, transport=self._transport) as client:
            return client.post(
                self._url,
                json={"events": list(payloads)},
                headers={"Authorization": f"Bearer {self._token.get()}"},
            )


def _select_pending(connection: Connection, batch_size: int) -> list[PendingEvent]:
    rows = connection.execute(
        text(
            "SELECT event_id, payload, attempts FROM audit_outbox "
            "WHERE status = 'PENDING' AND next_attempt_at <= now() "
            "ORDER BY next_attempt_at, created_at "
            "LIMIT :limit FOR UPDATE SKIP LOCKED"
        ),
        {"limit": batch_size},
    ).all()
    return [PendingEvent(str(row.event_id), dict(row.payload), row.attempts) for row in rows]


def _mark_sent(connection: Connection, event_ids: Sequence[str], status_code: int) -> None:
    if event_ids:
        connection.execute(
            text(
                "UPDATE audit_outbox SET status = 'SENT', sent_at = now(), attempts = attempts + 1, "
                "last_status_code = :status, last_error_code = NULL "
                "WHERE event_id = ANY(CAST(:ids AS uuid[]))"
            ),
            {"ids": list(event_ids), "status": status_code},
        )


def _reschedule(
    connection: Connection,
    events: Sequence[PendingEvent],
    settings: WorkerSettings,
    *,
    status_code: int | None,
    error_code: str,
    maximum: bool,
) -> None:
    for event in events:
        delay = backoff_seconds(event.attempts + 1, settings, maximum=maximum)
        connection.execute(
            text(
                "UPDATE audit_outbox SET attempts = attempts + 1, "
                "next_attempt_at = now() + make_interval(secs => :delay), "
                "last_status_code = :status, last_error_code = :error "
                "WHERE event_id = CAST(:id AS uuid)"
            ),
            {"delay": delay, "status": status_code, "error": error_code[:80], "id": event.event_id},
        )


def _json(response: httpx.Response) -> dict[str, Any]:
    try:
        body = response.json()
    except ValueError:
        return {}
    return body if isinstance(body, dict) else {}


def _rejected_indexes(response: httpx.Response, size: int) -> set[int]:
    """Índices del lote señalados por Audit en un `409` o `422`; todos si no se pueden identificar."""
    body = _json(response)
    indexes: set[int] = set()

    for conflict in body.get("conflicts") or []:
        if isinstance(conflict, dict) and isinstance(conflict.get("index"), int):
            indexes.add(conflict["index"])

    for error in body.get("errors") or []:
        match = _EVENT_INDEX.match(str(error.get("field", ""))) if isinstance(error, dict) else None
        if match:
            indexes.add(int(match.group(1)))

    valid = {index for index in indexes if 0 <= index < size}
    return valid or set(range(size))


def _error_code(response: httpx.Response) -> str:
    code = _json(response).get("code")
    return str(code) if code else f"HTTP_{response.status_code}"


def run_once(engine: Engine, client: AuditClient, settings: WorkerSettings) -> CycleResult:
    """Ejecuta un ciclo completo de entrega."""
    result = CycleResult()

    with engine.begin() as connection:
        pending = _select_pending(connection, settings.batch_size)
        result.selected = len(pending)

        while pending:
            try:
                response = client.send_batch([event.payload for event in pending])
            except (httpx.HTTPError, TokenUnavailableError) as exc:
                cause = type(exc).__name__
                logger.warning(
                    "Audit no disponible; se reintentará eventos=%s causa=%s", len(pending), cause
                )
                _reschedule(connection, pending, settings, status_code=None, error_code=cause, maximum=False)
                result.retried.extend(event.event_id for event in pending)
                break

            status = response.status_code

            if status in (200, 201):
                confirmed = {
                    str(item.get("event_id"))
                    for item in _json(response).get("items") or []
                    if isinstance(item, dict) and item.get("outcome") in {"CREATED", "ALREADY_EXISTS"}
                }
                sent = [event.event_id for event in pending if event.event_id in confirmed]
                missing = [event for event in pending if event.event_id not in confirmed]
                _mark_sent(connection, sent, status)
                result.sent.extend(sent)
                if missing:
                    _reschedule(
                        connection, missing, settings, status_code=status,
                        error_code="UNCONFIRMED", maximum=False,
                    )
                    result.retried.extend(event.event_id for event in missing)
                logger.info("Eventos de auditoría confirmados cantidad=%s", len(sent))
                break

            if status in (409, 422):
                indexes = _rejected_indexes(response, len(pending))
                rejected = [event for index, event in enumerate(pending) if index in indexes]
                code = _error_code(response)
                for event in rejected:
                    logger.error(
                        "Evento de auditoría rechazado por Audit event_id=%s estado=%s code=%s "
                        "intentos=%s; se reintentará con el intervalo máximo",
                        event.event_id, status, code, event.attempts + 1,
                    )
                _reschedule(connection, rejected, settings, status_code=status, error_code=code, maximum=True)
                result.rejected.extend(event.event_id for event in rejected)
                pending = [event for index, event in enumerate(pending) if index not in indexes]
                continue

            if status in (401, 403):
                code = _error_code(response)
                logger.error(
                    "Audit rechazó la identidad del emisor estado=%s code=%s eventos=%s",
                    status, code, len(pending),
                )
                _reschedule(connection, pending, settings, status_code=status, error_code=code, maximum=True)
                result.rejected.extend(event.event_id for event in pending)
                break

            retryable = status >= 500 or status in RETRYABLE_STATUSES
            code = _error_code(response)
            logger.warning(
                "Respuesta no confirmada de Audit estado=%s code=%s eventos=%s",
                status, code, len(pending),
            )
            _reschedule(
                connection, pending, settings, status_code=status, error_code=code,
                maximum=not retryable,
            )
            (result.retried if retryable else result.rejected).extend(event.event_id for event in pending)
            break

    return result


def write_heartbeat(path: str) -> None:
    Path(path).write_text(str(time.time()), encoding="utf-8")


def heartbeat_is_fresh(settings: WorkerSettings, *, now: float | None = None) -> bool:
    try:
        last = float(Path(settings.heartbeat_file).read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return False
    return ((now or time.time()) - last) <= settings.heartbeat_max_age_seconds


class Worker:
    """Proceso de larga duración; termina el ciclo en curso al recibir la señal de parada."""

    def __init__(
        self,
        settings: WorkerSettings,
        *,
        engine: Engine | None = None,
        client: AuditClient | None = None,
    ) -> None:
        self.settings = settings
        self.engine = engine or create_engine(
            settings.database_url, pool_pre_ping=True, connect_args={"connect_timeout": 5}
        )
        self.client = client or AuditClient(settings)
        self.stop_event = threading.Event()

    def run(self) -> None:
        logger.info("audit-outbox-worker iniciado cliente=%s", self.settings.client_id)

        while not self.stop_event.is_set():
            try:
                result = run_once(self.engine, self.client, self.settings)
                if result.selected:
                    logger.info(
                        "Ciclo de outbox seleccionados=%s enviados=%s reintentos=%s rechazados=%s",
                        result.selected, len(result.sent), len(result.retried), len(result.rejected),
                    )
            except Exception as exc:  # la base del emisor puede estar caída: se reintenta
                logger.error("Ciclo de outbox fallido causa=%s", type(exc).__name__)

            write_heartbeat(self.settings.heartbeat_file)
            self.stop_event.wait(self.settings.poll_interval_seconds)

        logger.info("audit-outbox-worker detenido")
