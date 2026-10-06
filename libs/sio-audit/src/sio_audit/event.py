"""Contrato del evento de auditoría, independiente del transporte (versión 1).

Define el evento que envía un emisor (FR-010), su preparación (recorte de
textos, redacción y validación de formatos y límites; R-07, R-08) y su forma
canónica, sobre la que se calcula la huella de idempotencia (R-04, FR-018).

La misma preparación la usan el emisor (`sio_audit.outbox`) y Audit Service,
de modo que un evento inválido falla al guardarse en la outbox y no al enviarse.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sio_audit.redaction import MAX_DEPTH, redact

CONTRACT_VERSION = 1

ACTION_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]{0,49}$")
ENTITY_TYPE_PATTERN = re.compile(r"^[A-Z][A-Za-z0-9]{0,59}$")
RESULTS = frozenset({"SUCCESS", "FAILURE"})

USERNAME_MAX_LENGTH = 160
REASON_MAX_LENGTH = 2000
VALUES_MAX_BYTES = 64 * 1024
DEFAULT_MAX_CLOCK_SKEW_SECONDS = 300

EVENT_FIELDS = (
    "event_id",
    "company_id",
    "branch_id",
    "application_user_id",
    "keycloak_user_id",
    "username_snapshot",
    "action",
    "entity_type",
    "entity_id",
    "previous_values",
    "new_values",
    "redacted_paths",
    "result",
    "reason",
    "request_id",
    "correlation_id",
    "occurred_at",
)
"""Campos del contrato, en el orden canónico (data-model.md)."""

_UUID_FIELDS = (
    "event_id",
    "company_id",
    "branch_id",
    "application_user_id",
    "keycloak_user_id",
    "entity_id",
    "request_id",
    "correlation_id",
)


@dataclass(frozen=True, slots=True)
class FieldError:
    """Error de validación de un campo del evento."""

    field: str
    message: str
    code: str = "VALIDATION_ERROR"


class InvalidAuditEventError(ValueError):
    """El evento no cumple el contrato; `errors` indica cada campo inválido."""

    def __init__(self, errors: Sequence[FieldError]) -> None:
        self.errors = tuple(errors)
        fields = ", ".join(error.field for error in self.errors)
        super().__init__(f"Evento de auditoría inválido: {fields}")


@dataclass(frozen=True, slots=True)
class AuditEvent:
    """Evento de auditoría tal como lo envía un emisor (contrato v1)."""

    event_id: UUID
    action: str
    entity_type: str
    result: str
    occurred_at: datetime
    company_id: UUID | None = None
    branch_id: UUID | None = None
    application_user_id: UUID | None = None
    keycloak_user_id: UUID | None = None
    username_snapshot: str | None = None
    entity_id: UUID | None = None
    previous_values: dict[str, Any] | None = None
    new_values: dict[str, Any] | None = None
    redacted_paths: tuple[str, ...] = field(default=())
    reason: str | None = None
    request_id: UUID | None = None
    correlation_id: UUID | None = None


# --------------------------------------------------------------------------
# Forma canónica
# --------------------------------------------------------------------------


def format_timestamp(value: datetime) -> str:
    """`occurred_at` en UTC con microsegundos (`YYYY-MM-DDTHH:MM:SS.ffffffZ`)."""
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def to_canonical_dict(event: AuditEvent) -> dict[str, Any]:
    """Evento como diccionario JSON en su forma canónica (data-model.md)."""
    data: dict[str, Any] = {}

    for name in EVENT_FIELDS:
        value = getattr(event, name)

        if name in _UUID_FIELDS:
            data[name] = None if value is None else str(value).lower()
        elif name == "occurred_at":
            data[name] = format_timestamp(value)
        elif name == "redacted_paths":
            data[name] = sorted(set(value))
        else:
            data[name] = value

    return data


def dumps_canonical(value: Any) -> str:
    """Serialización canónica: claves ordenadas, sin espacios, UTF-8 literal."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_json(event: AuditEvent) -> str:
    """Forma canónica completa del evento."""
    return dumps_canonical(to_canonical_dict(event))


def content_hash(event: AuditEvent, source_service: str) -> str:
    """Huella de idempotencia: SHA-256 de la forma canónica más el emisor (R-04)."""
    payload = f"{canonical_json(event)}\n{source_service}".encode()
    return hashlib.sha256(payload).hexdigest()


def from_canonical_dict(data: Mapping[str, Any]) -> AuditEvent:
    """Reconstruye un evento desde su forma canónica (p. ej. el `payload` de la outbox)."""
    values: dict[str, Any] = {}

    for name in EVENT_FIELDS:
        value = data.get(name)

        if name in _UUID_FIELDS:
            values[name] = None if value is None else UUID(str(value))
        elif name == "occurred_at":
            values[name] = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        elif name == "redacted_paths":
            values[name] = tuple(value or ())
        else:
            values[name] = value

    return AuditEvent(**values)


# --------------------------------------------------------------------------
# Preparación y validación
# --------------------------------------------------------------------------


def _depth(value: Any) -> int:
    if isinstance(value, Mapping):
        return 1 + max((_depth(item) for item in value.values()), default=0)

    if isinstance(value, list):
        return 1 + max((_depth(item) for item in value), default=0)

    return 0


def _trimmed(value: str | None) -> str | None:
    return value.strip() if isinstance(value, str) else value


def _validate_values(name: str, value: Any, errors: list[FieldError]) -> None:
    if value is None:
        return

    if not isinstance(value, Mapping):
        errors.append(FieldError(name, "Debe ser un objeto JSON."))
        return

    if _depth(value) > MAX_DEPTH:
        errors.append(FieldError(name, f"Supera {MAX_DEPTH} niveles de anidamiento."))
        return

    if len(dumps_canonical(value).encode("utf-8")) > VALUES_MAX_BYTES:
        errors.append(FieldError(name, "Supera el tamaño máximo de 64 KB."))


def _validate_text(
    name: str,
    value: str | None,
    max_length: int,
    errors: list[FieldError],
) -> None:
    if value is None:
        return

    if not value:
        errors.append(FieldError(name, "No puede estar vacío."))
    elif len(value) > max_length:
        errors.append(FieldError(name, f"Supera {max_length} caracteres."))


def validate_event(
    event: AuditEvent,
    *,
    now: datetime | None = None,
    max_clock_skew_seconds: int = DEFAULT_MAX_CLOCK_SKEW_SECONDS,
) -> list[FieldError]:
    """Valida formatos y límites de un evento ya recortado y redactado (R-08).

    Args:
        event: Evento a validar.
        now: Hora de referencia para el límite de `occurred_at` hacia el futuro;
            `None` omite esa comprobación (el emisor no la aplica; Audit sí).
        max_clock_skew_seconds: Tolerancia hacia el futuro.
    """
    errors: list[FieldError] = []

    for name in _UUID_FIELDS:
        value = getattr(event, name)
        if value is not None and not isinstance(value, UUID):
            errors.append(FieldError(name, "Debe ser un UUID."))

    if event.event_id is None:
        errors.append(FieldError("event_id", "Es obligatorio."))

    if not isinstance(event.action, str) or not ACTION_PATTERN.fullmatch(event.action):
        errors.append(
            FieldError("action", "Debe usar mayúsculas y guion bajo (p. ej. CHANGE_PRICE), hasta 50.")
        )

    if not isinstance(event.entity_type, str) or not ENTITY_TYPE_PATTERN.fullmatch(event.entity_type):
        errors.append(
            FieldError("entity_type", "Debe ser el nombre de la entidad en PascalCase, hasta 60.")
        )

    if event.result not in RESULTS:
        errors.append(FieldError("result", "Debe ser SUCCESS o FAILURE."))

    if not isinstance(event.occurred_at, datetime) or event.occurred_at.tzinfo is None:
        errors.append(FieldError("occurred_at", "Debe incluir zona horaria."))
    elif now is not None and event.occurred_at > now + timedelta(seconds=max_clock_skew_seconds):
        errors.append(FieldError("occurred_at", "No puede estar en el futuro."))

    if event.branch_id is not None and event.company_id is None:
        errors.append(FieldError("branch_id", "Una sucursal exige company_id."))

    _validate_text("username_snapshot", event.username_snapshot, USERNAME_MAX_LENGTH, errors)
    _validate_text("reason", event.reason, REASON_MAX_LENGTH, errors)
    _validate_values("previous_values", event.previous_values, errors)
    _validate_values("new_values", event.new_values, errors)

    if any(not isinstance(path, str) or not path.strip() for path in event.redacted_paths):
        errors.append(FieldError("redacted_paths", "Debe contener rutas de texto no vacías."))

    return errors


def prepare_event(
    event: AuditEvent,
    *,
    now: datetime | None = None,
    max_clock_skew_seconds: int = DEFAULT_MAX_CLOCK_SKEW_SECONDS,
) -> AuditEvent:
    """Recorta, redacta y valida un evento (FR-017b: todo sobre el contenido redactado).

    Raises:
        InvalidAuditEventError: Si el evento no cumple el contrato.
    """
    paths = tuple(event.redacted_paths or ())

    if len(paths) != len(set(paths)):
        raise InvalidAuditEventError([FieldError("redacted_paths", "No puede repetir rutas.")])

    redaction = redact(event.previous_values, event.new_values, paths)
    prepared = replace(
        event,
        username_snapshot=_trimmed(event.username_snapshot),
        reason=_trimmed(event.reason),
        previous_values=redaction.previous_values,
        new_values=redaction.new_values,
        redacted_paths=redaction.paths,
    )

    errors = validate_event(prepared, now=now, max_clock_skew_seconds=max_clock_skew_seconds)

    if errors:
        raise InvalidAuditEventError(errors)

    return prepared
