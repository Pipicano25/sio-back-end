"""Procesamiento de las aplicaciones automáticas de precio (spec 021: FR-021-21..26; RC-021-7..10).

Cada aplicación (una lista y una presentación) se procesa en **su propia transacción**, con un bloqueo consultivo por
(lista, presentación) y revalidando bajo bloqueo que siga siendo procesable (orden por secuencia, FR-021-22). Así un
fallo en una lista no deshace las demás (CP-39) y dos instancias del worker no aplican dos veces (CP-T09).

Orden de decisión (FR-021-23, `domain.automatic_pricing.decide`): lista no vigente → moneda distinta → presentación
inactiva → costo ≤ 0 → sin política (finaliza el precio de esta lista) → precio igual (`UNCHANGED`) → `APPLIED`.

Reglas de precios (Spec 019 reutilizada, R-07):
- Con política, se cancelan **siempre** los precios futuros de esa lista y presentación (aclaración del 2026-10-15),
  como `INACTIVE` con `closure_reason = AUTOMATIC_SUPERSEDED`.
- `APPLIED`: cierra el precio vigente en `now` y crea el nuevo `[now, NULL)` con `origin = AUTOMATIC` (M-2). El precio
  se toma sobre el vigente **al procesar**, aunque sea un precio manual posterior a la recepción (decisión aprobada 11).
- `UNCHANGED`: sin versión nueva; si el vigente tenía fin, se abre (`valid_to = NULL`) para no dejar un hueco al
  cancelar los futuros.
- `ENDED_NO_POLICY`: cierra el vigente en `now` y cancela los futuros con `closure_reason = NO_POLICY`.
- Los precios cerrados o cancelados por una aplicación no se reactivan ni se extienden (RC-021-9).

Resolución administrativa (A4, FR-021-27): solo desde `PENDING` o `FAILED`; deja la aplicación `RESOLVED` (final) sin
tocar precios, con quien la resolvió y el motivo. Así se liberan las siguientes de la misma lista y presentación
(CP-54). Toma el mismo bloqueo consultivo que el worker para no cruzarse con un procesamiento en curso.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from commercial_relationship_service.application import audit_events
from commercial_relationship_service.application.exceptions import ApplicationAlreadyFinalError
from commercial_relationship_service.application.mutation import touch
from commercial_relationship_service.domain.automatic_pricing import (
    Outcome,
    PriceEvaluation,
    decide,
    final_price,
    real_unit_cost,
    reference_cost,
)
from commercial_relationship_service.domain.currency import currency_places
from commercial_relationship_service.domain.status import ACTIVE
from commercial_relationship_service.infrastructure.models import (
    AUTOMATIC_FINAL_STATUSES,
    AutomaticPriceApplicationModel,
    AutomaticPriceUpdateRequestModel,
    CompanyProductModel,
    CompanyProductPresentationModel,
    PriceListItemModel,
    PriceListModel,
)

WORKER_ACTOR = "system:commercial-relationship-price-worker"
WORKER_USERNAME = "commercial-relationship-price-worker"
ENTITY = "AutomaticPriceApplication"
AUTOMATIC = "AUTOMATIC"
SUPERSEDED = "AUTOMATIC_SUPERSEDED"
NO_POLICY = "NO_POLICY"
FAILED = "FAILED"
RESOLVED = "RESOLVED"
INACTIVE = "INACTIVE"
DETAIL_MAX = 500

ACTION_BY_OUTCOME = {
    Outcome.APPLIED: audit_events.APPLY_AUTOMATIC_PRICE,
    Outcome.ENDED_NO_POLICY: audit_events.END_PRICE_WITHOUT_POLICY,
}


@dataclass(frozen=True, slots=True)
class Processed:
    application_id: UUID
    status: str


def _text(value: Decimal | None, places: int | None = None) -> str | None:
    if value is None:
        return None
    if places is not None:
        return format(Decimal(value).quantize(Decimal(1).scaleb(-places)), "f")
    return format(Decimal(value).normalize(), "f")


def list_effective(price_list: PriceListModel, now: datetime) -> bool:
    return (
        price_list.status == ACTIVE
        and (price_list.valid_from is None or price_list.valid_from <= now)
        and (price_list.valid_to is None or price_list.valid_to > now)
    )


class AutomaticPriceApplicationService:
    """Aplica una aplicación pendiente sobre los precios de la lista (worker de precios)."""

    def __init__(self, repository, *, interval_seconds: float, max_backoff_seconds: float) -> None:
        self._repository = repository
        self._interval = interval_seconds
        self._max_backoff = max_backoff_seconds

    def process(self, application_id: UUID) -> Processed | None:
        """Procesa la aplicación si sigue siendo procesable; `None` si otro worker la tomó o aún debe esperar."""
        repo = self._repository
        application = repo.get(AutomaticPriceApplicationModel, application_id)
        if application is None:
            return None
        repo.lock_queue(application.price_list_id, application.company_product_presentation_id)
        application = repo.application_for_update(application_id)
        if application is None or application.status in AUTOMATIC_FINAL_STATUSES or not repo.still_processable(application_id):
            repo.commit()
            return None

        now = repo.now()
        request = repo.get(AutomaticPriceUpdateRequestModel, application.request_id)
        price_list = repo.get(PriceListModel, application.price_list_id)
        presentation = repo.get(CompanyProductPresentationModel, application.company_product_presentation_id)
        product = repo.get(CompanyProductModel, request.company_product_id)

        current_cost = real_unit_cost(request.line_total, request.quantity)
        previous_cost = (
            real_unit_cost(request.previous_line_total, request.previous_quantity)
            if request.previous_line_total is not None
            else None
        )
        reference = reference_cost(current_cost, previous_cost)
        has_policy = application.policy_id is not None
        new_price = final_price(reference, application.markup_percentage, price_list.currency_code) if has_policy else None

        items = repo.prices_of(application.price_list_id, application.company_product_presentation_id)
        current = next((item for item in items if item.valid_from <= now and (item.valid_to is None or item.valid_to > now)), None)
        futures = [item for item in items if item.valid_from > now]

        outcome = decide(
            PriceEvaluation(
                list_effective=list_effective(price_list, now),
                currency_matches=price_list.currency_code == request.currency_code,
                presentation_active=presentation.status == ACTIVE and presentation.is_sellable and product.status == ACTIVE,
                current_unit_cost=current_cost,
                has_policy=has_policy,
                current_price=None if current is None else current.unit_price,
                has_future_prices=bool(futures),
                new_price=new_price,
            )
        )

        cancelled: list[UUID] = []
        new_item_id = None
        if outcome in (Outcome.APPLIED, Outcome.UNCHANGED, Outcome.ENDED_NO_POLICY):
            reason = NO_POLICY if outcome is Outcome.ENDED_NO_POLICY else SUPERSEDED
            for item in futures:
                item.status = INACTIVE
                item.closure_reason = reason
                item.automatic_application_id = application.id
                self._touch(item, now)
                cancelled.append(item.id)
                audit_events.track_update(
                    repo.session, item, action=audit_events.CANCEL_FUTURE_PRICE, entity_type="PriceListItem",
                    company_id=item.company_id, extra_new={"automatic_application_id": application.id},
                    reason=f"Precio futuro cancelado por la actualización automática ({outcome.value})",
                )
            # Las cancelaciones van a la base antes de abrir o cerrar el vigente: la unidad de trabajo ordena los
            # UPDATE por clave primaria y, sin este flush, abrir el vigente podría chocar con un futuro aún ACTIVE
            # en `ex_price_list_items_no_overlap`.
            repo.flush()
            if current is not None and outcome in (Outcome.APPLIED, Outcome.ENDED_NO_POLICY):
                current.valid_to = now
                current.closure_reason = reason
                current.automatic_application_id = application.id
                self._touch(current, now)
            elif current is not None and outcome is Outcome.UNCHANGED and current.valid_to is not None:
                current.valid_to = None  # sin hueco: el precio vigente queda abierto (M-2)
                self._touch(current, now)
            repo.flush()  # cierres y cancelaciones antes del alta (la exclusión de vigencias los ve)
            if outcome is Outcome.APPLIED:
                new_item = PriceListItemModel(
                    id=uuid4(),
                    company_id=application.company_id,
                    price_list_id=application.price_list_id,
                    company_product_id=request.company_product_id,
                    company_product_presentation_id=application.company_product_presentation_id,
                    unit_price=new_price,
                    valid_from=now,
                    valid_to=None,
                    origin=AUTOMATIC,
                    automatic_application_id=application.id,
                    created_by=WORKER_ACTOR,
                    updated_by=WORKER_ACTOR,
                )
                repo.add(new_item)
                new_item_id = new_item.id

        places = currency_places(price_list.currency_code)
        application.current_unit_cost = current_cost
        application.previous_unit_cost = previous_cost
        application.reference_cost = reference
        application.previous_price = None if current is None else current.unit_price
        application.previous_price_item_id = None if current is None else current.id
        # FR-021-23: el precio solo se calcula con política (paso 6); los SKIPPED_* terminan antes (sin conversión).
        application.new_price = new_price if outcome in (Outcome.APPLIED, Outcome.UNCHANGED) else None
        application.new_price_item_id = new_item_id
        application.cancelled_future_item_ids = cancelled
        application.status = outcome.value
        application.attempts += 1
        application.first_attempt_at = application.first_attempt_at or now
        application.completed_at = now
        application.last_error_code = None
        application.last_error_detail = None
        application.updated_at = now
        application.updated_by = WORKER_ACTOR
        audit_events.track_update(
            repo.session,
            application,
            action=ACTION_BY_OUTCOME.get(outcome, audit_events.SKIP_AUTOMATIC_PRICE),
            entity_type=ENTITY,
            company_id=application.company_id,
            branch_id=request.branch_id,
            extra_new=self._trace(application, request, places),
            reason=None if outcome in ACTION_BY_OUTCOME else outcome.value,
        )
        repo.commit()
        return Processed(application.id, outcome.value)

    def fail(self, application_id: UUID, error: Exception) -> None:
        """Registra el fallo en una transacción nueva y programa el reintento con espera creciente (FR-021-26)."""
        repo = self._repository
        application = repo.application_for_update(application_id)
        if application is None or application.status in AUTOMATIC_FINAL_STATUSES:
            repo.commit()
            return
        now = repo.now()
        code = getattr(error, "code", None) or type(error).__name__
        detail = (getattr(error, "message", None) or str(error) or code)[:DETAIL_MAX]
        changed = application.last_error_code != code or application.status != FAILED
        application.attempts += 1
        application.first_attempt_at = application.first_attempt_at or now
        application.status = FAILED
        application.last_error_code = code[:60]
        application.last_error_detail = detail
        backoff = min(self._max_backoff, self._interval * (2 ** min(application.attempts, 20)))
        application.next_attempt_at = now + timedelta(seconds=backoff)
        application.updated_at = now
        application.updated_by = WORKER_ACTOR
        if changed:  # primer fallo y cada cambio de error (FR-021-33)
            audit_events.track_update(
                repo.session, application, action=audit_events.FAIL_AUTOMATIC_PRICE, entity_type=ENTITY,
                company_id=application.company_id, extra_new={"last_error_code": application.last_error_code},
                reason=detail,
            )
        repo.commit()

    @staticmethod
    def _touch(item: PriceListItemModel, now: datetime) -> None:
        item.updated_at = now
        item.updated_by = WORKER_ACTOR

    @staticmethod
    def _trace(application: AutomaticPriceApplicationModel, request: AutomaticPriceUpdateRequestModel, places: int) -> dict[str, Any]:
        """Trazabilidad de FR-021-33: recepción, lista, presentación, política, costos, precios e intentos."""
        return {
            "purchase_id": request.purchase_id,
            "purchase_detail_id": request.purchase_detail_id,
            "sequence": request.sequence,
            "price_list_id": application.price_list_id,
            "company_product_presentation_id": application.company_product_presentation_id,
            "policy_id": application.policy_id,
            "markup_percentage": _text(application.markup_percentage, 4),
            "current_unit_cost": _text(application.current_unit_cost),
            "previous_unit_cost": _text(application.previous_unit_cost),
            "reference_cost": _text(application.reference_cost),
            "previous_price": _text(application.previous_price, places),
            "new_price": _text(application.new_price, places),
            "new_price_item_id": application.new_price_item_id,
            "cancelled_future_item_ids": list(application.cancelled_future_item_ids),
            "status": application.status,
            "received_at": request.received_at,
            "received_by_user_id": request.received_by_user_id,
            "attempts": application.attempts,
            "first_attempt_at": application.first_attempt_at,
            "completed_at": application.completed_at,
        }


class AutomaticPriceResolutionService:
    """Resolución administrativa de una aplicación que no se completa sola (A4)."""

    def __init__(self, repository) -> None:
        self._repository = repository

    def resolve(self, current: AutomaticPriceApplicationModel, *, version: int, reason: str, actor: str):
        repo = self._repository
        repo.lock_queue(current.price_list_id, current.company_product_presentation_id)
        application = repo.load_for_update(current.id, expected_version=version)
        if application.status in AUTOMATIC_FINAL_STATUSES:
            repo.release()
            raise ApplicationAlreadyFinalError
        application.status = RESOLVED
        application.resolved_by = actor
        application.resolution_reason = reason
        application.completed_at = repo.database_now()
        touch(application, actor)
        return repo.save(
            application,
            duplicates={},
            audit=audit_events.spec(audit_events.RESOLVE_AUTOMATIC_PRICE, ENTITY, application.company_id, reason=reason),
        )
