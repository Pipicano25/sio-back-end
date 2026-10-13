"""Precio aplicable por lotes (FR-055, FR-056; R-10; DS-11; aclaración 2; H-03; spec 019).

Orden de resolución por línea (spec 019: el precio siempre es de una presentación):

1. Lista: la indicada (de la empresa, `ACTIVE` y vigente en `at`; si no, la
   línea informa `PRICE_LIST_NOT_APPLICABLE`) o, si no se indica, la
   predeterminada `ACTIVE` y vigente en la moneda del producto empresarial
   (si no la hay, `NO_APPLICABLE_PRICE_LIST`).
2. En la lista: **solo** el precio explícito de la presentación de la línea
   (`basis = PRESENTATION`). Sin él, `NO_PRICE_IN_LIST`.

No hay precios generales por producto, ni respaldo en el producto empresarial,
ni conversiones entre presentaciones. Los precios anteriores sin presentación
se ignoran. No persiste nada y no juzga la aptitud: el consumidor decide con los
estados informados.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from commercial_relationship_service.application.company_product_service import BATCH_LIMIT
from commercial_relationship_service.application.exceptions import BatchLimitExceededError
from commercial_relationship_service.domain.status import ACTIVE
from commercial_relationship_service.domain.validity import contains

PRICE_LIST_ITEM = "PRICE_LIST_ITEM"
NO_PRICE_IN_LIST = "NO_PRICE_IN_LIST"
NO_APPLICABLE_PRICE_LIST = "NO_APPLICABLE_PRICE_LIST"
PRICE_LIST_NOT_APPLICABLE = "PRICE_LIST_NOT_APPLICABLE"
NOT_FOUND = "NOT_FOUND"
PRESENTATION = "PRESENTATION"


@dataclass(frozen=True, slots=True)
class PriceLine:
    """Línea solicitada."""

    company_product_id: UUID
    company_product_presentation_id: UUID | None = None  # obligatorio en la API (spec 019)
    price_list_id: UUID | None = None
    line_id: str | None = None


@dataclass(frozen=True, slots=True)
class ResolvedPrice:
    """Resultado de una línea; los campos de precio son `None` si no hay precio."""

    line_id: str | None
    found: bool
    resolution: str
    basis: str | None = None
    unit_price: Decimal | None = None
    currency_code: str | None = None
    price_list_id: UUID | None = None
    price_list_item_id: UUID | None = None
    company_product_status: str | None = None
    presentation_status: str | None = None


class ApplicablePriceService:
    """Resuelve el precio de venta de hasta 100 líneas de una empresa."""

    def __init__(self, repository) -> None:
        self._repository = repository

    def resolve(self, company_id: UUID, lines: list[PriceLine], *, at: datetime | None) -> tuple[datetime, list[ResolvedPrice]]:
        if len(lines) > BATCH_LIMIT:
            raise BatchLimitExceededError(field="lines")

        if at is None:
            at = self._repository.database_now()
            self._repository.release()

        products, presentations, lists, items = self._repository.resolution_data(
            company_id,
            product_ids={line.company_product_id for line in lines},
            presentation_ids={
                line.company_product_presentation_id
                for line in lines
                if line.company_product_presentation_id is not None
            },
            list_ids={line.price_list_id for line in lines if line.price_list_id is not None},
            at=at,
        )
        defaults = {
            price_list.currency_code: price_list
            for price_list in lists.values()
            if price_list.is_default and price_list.status == ACTIVE
        }

        return at, [
            _resolve_line(line, at, products, presentations, lists, defaults, items) for line in lines
        ]


def _applicable(price_list: Any, at: datetime) -> bool:
    return price_list.status == ACTIVE and contains(price_list.valid_from, price_list.valid_to, at)


def _resolve_line(line: PriceLine, at: datetime, products, presentations, lists, defaults, items) -> ResolvedPrice:
    product = products.get(line.company_product_id)
    presentation = None

    if line.company_product_presentation_id is not None:
        presentation = presentations.get(line.company_product_presentation_id)

        # H-03: una presentación de otro producto no aparece en la consulta (misma regla que inexistente).
        if presentation is None or product is None or presentation.company_product_id != product.id:
            product = None

    if product is None:
        return ResolvedPrice(line_id=line.line_id, found=False, resolution=NOT_FOUND)

    states = {
        "company_product_status": product.status,
        "presentation_status": None if presentation is None else presentation.status,
    }
    explicit = line.price_list_id is not None

    if explicit:
        price_list = lists.get(line.price_list_id)

        if price_list is None or not _applicable(price_list, at):
            return ResolvedPrice(line_id=line.line_id, found=True, resolution=PRICE_LIST_NOT_APPLICABLE, **states)

    else:
        price_list = defaults.get(product.currency_code)

        if price_list is not None and not _applicable(price_list, at):
            price_list = None

    if price_list is None:
        return ResolvedPrice(line_id=line.line_id, found=True, resolution=NO_APPLICABLE_PRICE_LIST, **states)

    item = items.get((price_list.id, product.id, presentation.id)) if presentation is not None else None

    if item is None:
        # Spec 019: sin el precio explícito de la presentación no hay precio (ni general ni de respaldo).
        return ResolvedPrice(line_id=line.line_id, found=True, resolution=NO_PRICE_IN_LIST, **states)

    return ResolvedPrice(
        line_id=line.line_id,
        found=True,
        resolution=PRICE_LIST_ITEM,
        basis=PRESENTATION,
        unit_price=item.unit_price,
        currency_code=price_list.currency_code,
        price_list_id=price_list.id,
        price_list_item_id=item.id,
        **states,
    )
