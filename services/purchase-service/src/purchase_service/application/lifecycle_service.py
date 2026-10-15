"""Hitos logísticos (Historia 4; FR-035 a FR-038, DS-08; research.md R-10).

El registro bloquea la compra (`FOR UPDATE`) para serializar hitos concurrentes de la
misma compra, sin cambiar su `version`. Los hitos son inmutables; un error se corrige
con un nuevo registro del mismo tipo, que pasa a ser el vigente.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from purchase_service.application import audit_events as audit
from purchase_service.application.branch_access import require_branch_access
from purchase_service.application.exceptions import (
    EventNotAllowedInStatusError,
    PurchaseNotReceivedError,
    NotFoundError,
    ValidationFailedError,
    field_error,
)
from purchase_service.application.purchase_service import Actor
from purchase_service.domain.lifecycle import (
    REQUIRES_RECEIPT,
    EventInFutureError,
    EventNotAllowedError,
    EventOrderError,
    EventRecord,
    Interval,
    check_new_event,
    current_events,
    intervals,
)
from purchase_service.domain.status import CONFIRMED
from purchase_service.infrastructure.models import PurchaseLifecycleEvent
from purchase_service.infrastructure.repository import PurchaseRepository


@dataclass(frozen=True, slots=True)
class Timeline:
    events: list[PurchaseLifecycleEvent]
    current: dict[str, UUID]
    intervals: list[Interval]
    total_lead_time_hours: Decimal | None


def _records(events: list[PurchaseLifecycleEvent]) -> list[EventRecord]:
    return [EventRecord(event.id, event.event_type, event.occurred_at, event.created_at) for event in events]


class LifecycleService:
    def __init__(self, repository: PurchaseRepository, *, clock: Callable[[], datetime]) -> None:
        self._repo = repository
        self._clock = clock

    def record(
        self,
        company_id: UUID,
        purchase_id: UUID,
        event_type: str,
        occurred_at: datetime,
        source: str,
        notes: str | None,
        actor: Actor,
    ) -> PurchaseLifecycleEvent:
        purchase = self._repo.get_purchase(company_id, purchase_id)
        if purchase is None:
            raise NotFoundError()
        self._repo.end_read()
        operator = require_branch_access(actor.access, company_id, purchase.branch_id)

        try:
            self._repo.begin()
            locked = self._repo.lock_purchase(company_id, purchase_id)
            if locked is None:
                raise NotFoundError()
            now = self._clock()
            if locked.status == CONFIRMED and event_type in REQUIRES_RECEIPT and locked.inventory_operation_id is None:
                raise PurchaseNotReceivedError(event_type)
            try:
                check_new_event(locked.status, event_type, occurred_at, _records(self._repo.events(locked.id)), now)
            except EventNotAllowedError:
                raise EventNotAllowedInStatusError(event_type, locked.status) from None
            except EventInFutureError:
                raise ValidationFailedError(
                    [field_error("occurred_at", "EVENT_IN_FUTURE", "El hito no puede registrarse en el futuro.")]
                ) from None
            except EventOrderError as error:
                raise ValidationFailedError(
                    [
                        {
                            **field_error(
                                "occurred_at",
                                "EVENT_OUT_OF_ORDER",
                                f"El momento del hito es incoherente con el hito vigente {error.conflicting_type}.",
                            ),
                            "conflicting_event_type": error.conflicting_type,
                            "conflicting_event_id": str(error.conflicting_id),
                        }
                    ]
                ) from None

            event = PurchaseLifecycleEvent(
                id=uuid4(),
                company_id=company_id,
                purchase_id=locked.id,
                event_type=event_type,
                occurred_at=occurred_at,
                recorded_by_user_id=operator.application_user_id,
                source=source,
                notes=notes,
                created_at=now,
                created_by=actor.subject,
            )
            self._repo.add(event)
            self._repo.flush()
            audit.record(
                self._repo.session,
                action=audit.RECORD_LIFECYCLE_EVENT,
                entity_type=audit.LIFECYCLE_EVENT,
                entity_id=event.id,
                company_id=company_id,
                branch_id=locked.branch_id,
                application_user_id=operator.application_user_id,
                new_values={
                    "purchase_id": locked.id,
                    "event_type": event_type,
                    "occurred_at": occurred_at,
                    "source": source,
                },
            )
            self._repo.commit()
            return event
        except Exception:
            self._repo.rollback()
            raise

    def timeline(self, company_id: UUID, purchase_id: UUID) -> Timeline:
        purchase = self._repo.get_purchase(company_id, purchase_id)
        if purchase is None:
            raise NotFoundError()
        events = self._repo.events(purchase.id)
        records = _records(events)
        current = {event_type: record.id for event_type, record in current_events(records).items()}
        result, total = intervals(records)
        return Timeline(events, current, result, total)
