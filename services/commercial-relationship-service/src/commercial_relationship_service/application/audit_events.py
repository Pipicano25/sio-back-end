"""Registro de eventos de auditoría en la outbox (feature 016; research R-02, R-03).

Mecanismo común a los cuatro servicios auditados en la 016:

1. El repositorio (o servicio de aplicación) que modifica una entidad llama a
   `track_create`, `track_update` o `track_delete` **antes** del `commit`, justo después
   de aplicar los cambios al modelo. `track_update` calcula aquí los valores anteriores y
   nuevos con el historial de atributos del ORM (aún sin `flush`); si ningún campo
   considerado cambió, no registra nada (DS-05).
2. Un listener `before_commit` de la sesión hace `flush` (las creaciones ya tienen `id` y
   valores por defecto) y escribe cada evento con `sio_audit.outbox.record_audit_event` en
   la **misma transacción** (RC-01). Un `IntegrityError` sigue saliendo de `commit()`, por
   lo que la traducción de errores existente no cambia (RC-06).
3. Un `rollback` descarta los eventos pendientes: sin cambio no hay evento.

Valores (contracts/audit-actions.md): se excluyen `id`, `version`, `created_*` y
`updated_*`; los campos protegidos (DS-06, DS-09) se reemplazan por un marcador y su ruta
se declara en `redacted_paths`; nunca se guarda su valor ni un hash. Solo `SUCCESS`
(DS-02). Sin autor autenticado (p. ej. `seed`) no se audita.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from sio_audit.event import AuditEvent
from sio_audit.outbox import record_audit_event
from sqlalchemy import event, inspect
from sqlalchemy.sql import ClauseElement
from sqlalchemy.orm import Session

from commercial_relationship_service.audit_context import AuditActor, current_actor, current_request_id

TECHNICAL_FIELDS = frozenset({"id", "version", "created_at", "created_by", "updated_at", "updated_by"})
REGISTERED = "<registrado>"
MODIFIED = "<modificado>"
REMOVED = "<eliminado>"
PENDING_KEY = "sio_audit_pending_events"
BEFORE_KEY = "sio_audit_before_images"

ScopeValue = UUID | Callable[[Any], UUID | None] | None

PROTECTED_FIELDS: Mapping[str, frozenset[str]] = {}  # sin campos protegidos (DS-06/DS-09 no aplican)


def protected_fields(entity_type: str) -> frozenset[str]:
    return PROTECTED_FIELDS.get(entity_type, PROTECTED_FIELDS.get("*", frozenset()))


def jsonable(value: Any) -> Any:
    """Valor serializable y estable (UUID, fechas y `Decimal` como texto)."""
    if value is None or isinstance(value, bool | int | float | str):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, Decimal | UUID):
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set | frozenset):
        return [jsonable(item) for item in value]
    return str(value)


def _considered(model: Any) -> list[str]:
    return [attr.key for attr in inspect(model).mapper.column_attrs if attr.key not in TECHNICAL_FIELDS]


def _value(model: Any, key: str, raw: Any) -> Any:
    """Valor estable de una columna: los decimales con la escala de la columna (como en la base)."""
    if isinstance(raw, Decimal | int | float) and not isinstance(raw, bool):
        column = inspect(model).mapper.columns.get(key)
        scale = getattr(getattr(column, "type", None), "scale", None)
        if scale is not None:
            return str(Decimal(str(raw)).quantize(Decimal(1).scaleb(-scale)))
    return jsonable(raw)


def snapshot(model: Any) -> dict[str, Any]:
    """Campos considerados de la entidad (después del `flush`)."""
    return {key: _value(model, key, getattr(model, key)) for key in _considered(model)}


DEFERRED = object()
"""Valor nuevo calculado por la base (p. ej. `func.now()`): se lee después del `flush`."""


def changes(model: Any) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """Valores anteriores y nuevos de los campos considerados que cambiaron, o `None`."""
    state = inspect(model)
    previous: dict[str, Any] = {}
    new: dict[str, Any] = {}
    for key in _considered(model):
        history = state.attrs[key].history
        if not history.has_changes():
            continue
        old_value = _value(model, key, history.deleted[0]) if history.deleted else None
        added = history.added[0] if history.added else None
        if isinstance(added, ClauseElement):
            previous[key] = old_value
            new[key] = DEFERRED
            continue
        new_value = _value(model, key, added)
        if old_value != new_value:
            previous[key] = old_value
            new[key] = new_value
    return (previous, new) if new or previous else None


def spec(action: str, entity_type: str, company_id: ScopeValue = None, **extra: Any) -> dict[str, Any]:
    """Descripción de la acción para los repositorios que registran por parámetro (`audit=`)."""
    return {"action": action, "entity_type": entity_type, "company_id": company_id, **extra}


def remember(session: Session, model: Any) -> None:
    """Guarda la imagen previa de la entidad al cargarla para modificarla.

    Con imagen previa, `track_update` compara contra ella en lugar del historial del ORM, así un
    `flush` intermedio (p. ej. al retirar la marca de principal de otras filas) no pierde los
    valores anteriores.
    """
    session.info.setdefault(BEFORE_KEY, {})[id(model)] = snapshot(model)


def _changes_from(before: Mapping[str, Any], model: Any) -> tuple[dict[str, Any], dict[str, Any]] | None:
    previous: dict[str, Any] = {}
    new: dict[str, Any] = {}
    for key in _considered(model):
        raw = getattr(model, key)
        if isinstance(raw, ClauseElement):
            previous[key] = before.get(key)
            new[key] = DEFERRED
            continue
        value = _value(model, key, raw)
        if before.get(key) != value:
            previous[key] = before.get(key)
            new[key] = value
    return (previous, new) if new or previous else None


def status_action(model: Any, suffix: str) -> str:
    """`DEACTIVATE_`/`REACTIVATE_<suffix>` si cambia el estado (`status` o `is_active`); si no, `UPDATE_`."""
    attrs = inspect(model).attrs
    for name, inactive, active in (("status", "INACTIVE", "ACTIVE"), ("is_active", False, True)):
        if name not in attrs:
            continue
        history = attrs[name].history
        if history.has_changes() and history.added:
            if history.added[0] == inactive:
                return f"DEACTIVATE_{suffix}"
            if history.added[0] == active:
                return f"REACTIVATE_{suffix}"
    return f"UPDATE_{suffix}"


def protect(
    entity_type: str,
    previous: Mapping[str, Any] | None,
    new: Mapping[str, Any] | None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, list[str]]:
    """Reemplaza los campos protegidos por su marcador y devuelve las rutas ocultadas."""
    fields = protected_fields(entity_type)
    out_previous = None if previous is None else dict(previous)
    out_new = None if new is None else dict(new)
    paths: list[str] = []
    for key in sorted(fields):
        before = None if previous is None else previous.get(key)
        after = None if new is None else new.get(key)
        in_previous = previous is not None and key in previous
        in_new = new is not None and key in new
        if not in_previous and not in_new:
            continue
        if previous is None:  # creación
            marker_new = REGISTERED if after is not None else None
            marker_previous = None
        elif new is None:  # eliminación
            marker_previous = REMOVED if before is not None else None
            marker_new = None
        elif before is None:
            marker_previous, marker_new = None, REGISTERED
        elif after is None:
            marker_previous, marker_new = REMOVED, None
        else:
            marker_previous, marker_new = MODIFIED, MODIFIED
        if in_previous and out_previous is not None:
            out_previous[key] = marker_previous
            if before is not None:
                paths.append(f"previous_values.{key}")
        if in_new and out_new is not None:
            out_new[key] = marker_new
            if after is not None:
                paths.append(f"new_values.{key}")
    return out_previous, out_new, paths


@dataclass
class _Pending:
    model: Any
    kind: str
    action: str
    entity_type: str
    actor: AuditActor
    request_id: UUID | None
    occurred_at: datetime
    company_id: ScopeValue = None
    branch_id: ScopeValue = None
    application_user_id: ScopeValue = None
    entity_id: ScopeValue = None
    previous: dict[str, Any] | None = None
    new: dict[str, Any] | None = None
    extra_previous: dict[str, Any] = field(default_factory=dict)
    extra_new: dict[str, Any] = field(default_factory=dict)
    reason: str | None = None


def _add(session: Session, pending: _Pending) -> None:
    # El evento pertenece a la transacción en curso: si aún no empezó, se abre ahora para que
    # un `rollback` posterior (que sí emite `after_soft_rollback`) siempre lo descarte.
    if not session.in_transaction():
        session.begin()
    session.info.setdefault(PENDING_KEY, []).append(pending)


def _base(model, kind, action, entity_type, **kwargs) -> _Pending | None:
    actor = current_actor()
    if actor is None:
        return None
    return _Pending(
        model=model,
        kind=kind,
        action=action,
        entity_type=entity_type,
        actor=actor,
        request_id=current_request_id(),
        occurred_at=datetime.now(UTC),
        **kwargs,
    )


def track_create(
    session: Session,
    model: Any,
    *,
    action: str,
    entity_type: str,
    company_id: ScopeValue = None,
    branch_id: ScopeValue = None,
    application_user_id: ScopeValue = None,
    extra_previous: Mapping[str, Any] | None = None,
    extra_new: Mapping[str, Any] | None = None,
    reason: str | None = None,
) -> bool:
    """Registra la creación; los valores se toman tras el `flush` del `commit`.

    `extra_previous` permite registrar, por ejemplo, `previous_primary_id` cuando la nueva entidad
    reemplaza a otra como principal (contrato, `SET_PRIMARY_*`/`CHANGE_PRIMARY_*`).
    """
    pending = _base(
        model, "CREATE", action, entity_type,
        company_id=company_id, branch_id=branch_id, application_user_id=application_user_id,
        extra_previous=dict(extra_previous or {}), extra_new=dict(extra_new or {}), reason=reason,
    )
    if pending is None:
        return False
    _add(session, pending)
    return True


def track_update(
    session: Session,
    model: Any,
    *,
    action: str,
    entity_type: str,
    company_id: ScopeValue = None,
    branch_id: ScopeValue = None,
    application_user_id: ScopeValue = None,
    extra_previous: Mapping[str, Any] | None = None,
    extra_new: Mapping[str, Any] | None = None,
    reason: str | None = None,
) -> bool:
    """Registra los campos que cambiaron (ahora, antes del `flush`); sin cambios → nada."""
    before = session.info.get(BEFORE_KEY, {}).get(id(model))
    diff = _changes_from(before, model) if before is not None else changes(model)
    if diff is None and not extra_new and not extra_previous:
        return False
    pending = _base(
        model, "UPDATE", action, entity_type,
        company_id=company_id, branch_id=branch_id, application_user_id=application_user_id,
        previous=diff[0] if diff else {}, new=diff[1] if diff else {},
        extra_previous=dict(extra_previous or {}), extra_new=dict(extra_new or {}), reason=reason,
    )
    if pending is None:
        return False
    _add(session, pending)
    return True


def track_delete(
    session: Session,
    model: Any,
    *,
    action: str,
    entity_type: str,
    company_id: ScopeValue = None,
    branch_id: ScopeValue = None,
    application_user_id: ScopeValue = None,
    reason: str | None = None,
) -> bool:
    """Registra la eliminación con los valores eliminados (antes de `session.delete`)."""
    pending = _base(
        model, "DELETE", action, entity_type,
        company_id=company_id, branch_id=branch_id, application_user_id=application_user_id,
        entity_id=getattr(model, "id", None), previous=snapshot(model), reason=reason,
    )
    if pending is None:
        return False
    _add(session, pending)
    return True


def _resolve(value: ScopeValue, model: Any) -> UUID | None:
    return value(model) if callable(value) else value


def _write(session: Session, pending: _Pending) -> UUID:
    model = pending.model
    if pending.kind == "CREATE":
        previous, new = None, snapshot(model)
    elif pending.kind == "DELETE":
        previous, new = pending.previous, None
    else:
        previous = pending.previous
        new = {
            key: _value(model, key, getattr(model, key)) if value is DEFERRED else value
            for key, value in (pending.new or {}).items()
        }
    if pending.extra_previous:
        previous = {**(previous or {}), **jsonable(pending.extra_previous)}
    if pending.extra_new:
        new = {**(new or {}), **jsonable(pending.extra_new)}
    previous, new, paths = protect(pending.entity_type, previous, new)
    entity_id = _resolve(pending.entity_id, model) or model.id
    subject = pending.actor.subject
    try:
        keycloak_user_id = UUID(subject)
    except ValueError:
        keycloak_user_id = None
    return record_audit_event(
        session,
        AuditEvent(
            event_id=None,
            action=pending.action,
            entity_type=pending.entity_type,
            entity_id=entity_id,
            result="SUCCESS",
            occurred_at=pending.occurred_at,
            company_id=_resolve(pending.company_id, model),
            branch_id=_resolve(pending.branch_id, model),
            application_user_id=_resolve(pending.application_user_id, model),
            keycloak_user_id=keycloak_user_id,
            username_snapshot=pending.actor.username,
            previous_values=previous,
            new_values=new,
            redacted_paths=tuple(paths),
            reason=pending.reason,
            request_id=pending.request_id,
        ),
    )


@event.listens_for(Session, "before_commit")
def _write_pending(session: Session) -> None:
    pending = session.info.pop(PENDING_KEY, None)
    if not pending:
        return
    session.flush()
    for item in pending:
        _write(session, item)


@event.listens_for(Session, "after_commit")
def _forget_before_images(session: Session) -> None:
    session.info.pop(BEFORE_KEY, None)


@event.listens_for(Session, "after_rollback")
def _discard_pending(session: Session) -> None:
    session.info.pop(PENDING_KEY, None)
    session.info.pop(BEFORE_KEY, None)


@event.listens_for(Session, "after_soft_rollback")
def _discard_pending_soft(session: Session, previous_transaction) -> None:
    session.info.pop(PENDING_KEY, None)
    session.info.pop(BEFORE_KEY, None)


# Catálogo de acciones y tipos de entidad del servicio (contracts/audit-actions.md).
from commercial_relationship_service.application.audit_actions import *  # noqa: E402, F401, F403
