"""Hechos de costo de cada recepción para la actualización automática de precios (spec 021: FR-021-14, FR-021-15).

Se escriben en la **misma transacción T2** que completa la recepción (Transactional Outbox, EXC-001): si T2 se
revierte, no queda solicitud; si confirma, la solicitud existe aunque Commercial Relationship no esté disponible
(RC-021-3).

- **Serie por presentación en la empresa** (R-03): cada recepción recibe la secuencia contigua siguiente bajo bloqueo
  (consultivo y `FOR UPDATE`, en orden de `id` de presentación para evitar interbloqueos). Así dos recepciones
  simultáneas en sucursales distintas quedan ordenadas y la segunda se compara con la primera (CP-46).
- **Costo anterior:** el último de la serie o, la primera vez, la última línea recibida antes de la spec 021. Es el
  costo **real** de esa recepción, nunca su referencia comercial (CP-04). Una anulación posterior no lo cambia (M-1).
- **Solo hechos** (DS-01): importe pagado de la línea (`total`, que ya incluye el impuesto y descuenta el descuento) y
  cantidad, sin dividir ni redondear. Commercial Relationship calcula costos unitarios, referencia y precio.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from purchase_service.infrastructure.models import (
    Purchase,
    PurchaseDetail,
    PurchasePresentationCostSeries,
    PurchasePriceUpdateOutbox,
)

CONTRACT_VERSION = 1
MONEY = Decimal("0.01")
QUANTITY = Decimal("0.0001")


def _money(value: Decimal | None) -> str | None:
    return None if value is None else format(Decimal(value).quantize(MONEY), "f")


def _quantity(value: Decimal | None) -> str | None:
    return None if value is None else format(Decimal(value).quantize(QUANTITY), "f")


def request_payload(
    purchase: Purchase,
    line: PurchaseDetail,
    *,
    sequence: int,
    previous_sequence: int | None,
    previous: tuple | None,
) -> dict:
    """Contrato v1 (`contracts/price-update-request.md`): decimales como texto, sin costos unitarios."""
    previous_detail, previous_total, previous_quantity = previous or (None, None, None)
    return {
        "contract_version": CONTRACT_VERSION,
        "purchase_detail_id": str(line.id),
        "purchase_id": str(purchase.id),
        "branch_id": str(purchase.branch_id),
        "company_product_id": str(line.company_product_id),
        "company_product_presentation_id": str(line.company_product_presentation_id),
        "sequence": sequence,
        "previous_sequence": previous_sequence,
        "currency_code": purchase.currency_code,
        "line_total": _money(line.total),
        "quantity": _quantity(line.quantity),
        "previous_purchase_detail_id": None if previous_detail is None else str(previous_detail),
        "previous_line_total": _money(previous_total),
        "previous_quantity": _quantity(previous_quantity),
        "received_at": purchase.received_at.isoformat(),
        "received_by_user_id": str(purchase.received_by_user_id),
    }


def record_price_update_facts(repository, purchase: Purchase, lines: list[PurchaseDetail], actor: str, now: datetime) -> None:
    """Avanza la serie de cada presentación y escribe una solicitud por línea en el outbox (dentro de T2)."""
    presentation_ids = [line.company_product_presentation_id for line in lines]
    series_by_presentation = repository.lock_cost_series(purchase.company_id, presentation_ids)
    missing = [presentation_id for presentation_id in presentation_ids if presentation_id not in series_by_presentation]
    earlier_lines = repository.previous_received_lines(purchase.company_id, missing, exclude_purchase_id=purchase.id)
    rows = []

    for line in sorted(lines, key=lambda item: str(item.company_product_presentation_id)):
        presentation_id = line.company_product_presentation_id
        series = series_by_presentation.get(presentation_id)

        if series is None:
            earlier = earlier_lines.get(presentation_id)
            sequence, previous_sequence = 1, None
            previous = None if earlier is None else (earlier.id, earlier.total, earlier.quantity)
            rows.append(
                PurchasePresentationCostSeries(
                    company_id=purchase.company_id,
                    company_product_presentation_id=presentation_id,
                    last_sequence=sequence,
                    last_purchase_detail_id=line.id,
                    last_line_total=line.total,
                    last_quantity=line.quantity,
                    created_at=now,
                    updated_at=now,
                )
            )
        else:
            sequence, previous_sequence = series.last_sequence + 1, series.last_sequence
            previous = (series.last_purchase_detail_id, series.last_line_total, series.last_quantity)
            series.last_sequence = sequence
            series.last_purchase_detail_id = line.id
            series.last_line_total = line.total
            series.last_quantity = line.quantity
            series.updated_at = now

        rows.append(
            PurchasePriceUpdateOutbox(
                id=uuid4(),
                company_id=purchase.company_id,
                company_product_presentation_id=presentation_id,
                sequence=sequence,
                purchase_id=purchase.id,
                purchase_detail_id=line.id,
                payload=request_payload(
                    purchase, line, sequence=sequence, previous_sequence=previous_sequence, previous=previous
                ),
                status="PENDING",
                attempts=0,
                next_attempt_at=now,
                created_at=now,
                created_by=actor,
            )
        )
    repository.add_all(rows)
    repository.flush()


# ---------------------------------------------------------------- entrega (worker, FR-021-16)

ACCEPTED, REJECTED = "ACCEPTED", "REJECTED"
NEVER = timedelta(days=36500)  # un `409` es un defecto: no se reintenta solo, queda visible para revisión


class PriceUpdateDeliveryService:
    """Entrega el outbox a Commercial Relationship en orden de secuencia por presentación.

    Solo se intenta la menor secuencia `PENDING` de cada (empresa, presentación): si falla, esa presentación espera y las
    demás siguen (CP-T04). Con `202` la solicitud queda `DELIVERED`; con `409`, `PENDING` con su error y sin reintento
    automático; ante caídas, tiempos agotados, `5xx`, `401` o `403`, reintento con espera creciente y tope.
    """

    def __init__(self, repository, gateway, *, interval_seconds: float, max_backoff_seconds: float, clock) -> None:
        self._repository = repository
        self._gateway = gateway
        self._interval = interval_seconds
        self._max_backoff = max_backoff_seconds
        self._clock = clock

    def run_once(self, limit: int = 100) -> dict[str, int]:
        counts = {"delivered": 0, "rejected": 0, "retry": 0}
        for request_id in self._repository.deliverable_heads(limit):
            self._repository.begin()
            request = self._repository.outbox_for_update(request_id)
            if request is None or request.status != "PENDING":
                self._repository.commit()
                continue
            self._repository.end_read()  # no retener bloqueos durante la llamada a CR
            result = self._gateway.submit(request.company_id, request.payload)
            now = self._clock()
            self._repository.begin()
            request = self._repository.outbox_for_update(request_id)
            if result.outcome == ACCEPTED:
                request.status = "DELIVERED"
                request.delivered_at = now
                request.last_error_code = None
                counts["delivered"] += 1
            else:
                request.attempts += 1
                request.last_error_code = (result.code or "UNKNOWN")[:60]
                request.last_error_at = now
                if result.outcome == REJECTED:
                    request.next_attempt_at = now + NEVER
                    counts["rejected"] += 1
                else:
                    request.next_attempt_at = now + timedelta(
                        seconds=min(self._max_backoff, self._interval * (2 ** min(request.attempts, 20)))
                    )
                    counts["retry"] += 1
            self._repository.commit()
        return counts
