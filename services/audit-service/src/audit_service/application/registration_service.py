"""Registro de eventos de auditoría (FR-010 a FR-021; RC-03 a RC-06).

Orden de cada evento: redactar → validar formatos y límites sobre el contenido
redactado → calcular la huella con el emisor del token → insertar o comparar
(`sio_audit.event.prepare_event`, la misma preparación que usan los emisores).

Un lote es atómico: se validan todos los eventos antes de escribir y cualquier
conflicto revierte la transacción completa (DS-02, R-05).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from sio_audit.event import AuditEvent, InvalidAuditEventError, content_hash, prepare_event

from audit_service.application.exceptions import EventIdConflictError, ValidationFailedError
from audit_service.application.ports import AuditEventRepository, InsertOutcome, NewAuditEventRow

_EVENT_ID_CONFLICT_MESSAGE = (
    "Ya existe un evento con ese event_id y un contenido o emisor distinto."
)


@dataclass(frozen=True, slots=True)
class Emitter:
    """Cuenta de servicio emisora (del token, nunca del cuerpo)."""

    subject: str
    source_service: str


@dataclass(frozen=True, slots=True)
class RegisteredEvent:
    """Evento registrado o existente."""

    index: int
    row: Any
    created: bool


class RegistrationService:
    """Caso de uso de registro de uno o varios eventos."""

    def __init__(self, repository: AuditEventRepository, *, max_clock_skew_seconds: int) -> None:
        self._repository = repository
        self._max_clock_skew_seconds = max_clock_skew_seconds

    def register(self, event: AuditEvent, emitter: Emitter) -> RegisteredEvent:
        """Registra un evento; `created=False` si ya existía con el mismo contenido."""
        return self._register([event], emitter, batch=False)[0]

    def register_batch(self, events: Sequence[AuditEvent], emitter: Emitter) -> list[RegisteredEvent]:
        """Registra un lote de forma atómica."""
        return self._register(events, emitter, batch=True)

    def _register(
        self, events: Sequence[AuditEvent], emitter: Emitter, *, batch: bool
    ) -> list[RegisteredEvent]:
        now = self._repository.database_now()
        rows: list[NewAuditEventRow] = []
        errors: list[dict[str, str]] = []
        seen: dict[Any, int] = {}

        for index, event in enumerate(events):
            prefix = f"events[{index}]." if batch else ""

            if batch and event.event_id in seen:
                errors.append(
                    {
                        "field": f"{prefix}event_id",
                        "message": f"Repite el event_id del evento {seen[event.event_id]}.",
                        "code": "VALIDATION_ERROR",
                    }
                )
                continue

            seen[event.event_id] = index

            try:
                prepared = prepare_event(
                    event, now=now, max_clock_skew_seconds=self._max_clock_skew_seconds
                )
            except InvalidAuditEventError as exc:
                errors.extend(
                    {"field": f"{prefix}{item.field}", "message": item.message, "code": item.code}
                    for item in exc.errors
                )
                continue

            rows.append(self._row(prepared, emitter))

        if errors:
            raise ValidationFailedError("La solicitud contiene datos inválidos.", errors=errors)

        try:
            outcomes = self._repository.insert_or_get(rows)
            conflicts = [
                (index, outcome) for index, outcome in enumerate(outcomes) if outcome.conflict
            ]

            if conflicts:
                self._repository.rollback()
                raise EventIdConflictError(
                    _EVENT_ID_CONFLICT_MESSAGE,
                    context=self._conflict_context(conflicts, batch=batch),
                )

            self._repository.commit()
        except BaseException:
            self._repository.rollback()
            raise

        return [
            RegisteredEvent(index=index, row=outcome.row, created=outcome.created)
            for index, outcome in enumerate(outcomes)
        ]

    @staticmethod
    def _conflict_context(
        conflicts: list[tuple[int, InsertOutcome]], *, batch: bool
    ) -> dict[str, Any]:
        if not batch:
            return {}
        return {
            "conflicts": [
                {"index": index, "event_id": str(outcome.event_id)} for index, outcome in conflicts
            ]
        }

    @staticmethod
    def _row(event: AuditEvent, emitter: Emitter) -> NewAuditEventRow:
        values = {
            "event_id": event.event_id,
            "company_id": event.company_id,
            "branch_id": event.branch_id,
            "application_user_id": event.application_user_id,
            "keycloak_user_id": event.keycloak_user_id,
            "username_snapshot": event.username_snapshot,
            "action": event.action,
            "entity_type": event.entity_type,
            "entity_id": event.entity_id,
            "previous_values": event.previous_values,
            "new_values": event.new_values,
            "redacted_paths": list(event.redacted_paths),
            "result": event.result,
            "reason": event.reason,
            "request_id": event.request_id,
            "correlation_id": event.correlation_id,
            "occurred_at": event.occurred_at,
            "source_service": emitter.source_service,
            "content_hash": content_hash(event, emitter.source_service),
            "created_by": emitter.subject,
            "updated_by": emitter.subject,
        }
        return NewAuditEventRow(
            event_id=event.event_id, values=values, content_hash=values["content_hash"]
        )
