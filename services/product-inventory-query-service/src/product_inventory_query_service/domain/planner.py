"""Planificador de consultas determinista (A-19 v2; FR-022-130 a FR-022-133, FR-022-65; research R-05).

Función pura: no hace E/S, no consulta cardinalidades ni importa adaptadores. Con la misma `QuerySpec` (sin
contar el cursor) y la misma política de lotes devuelve siempre el mismo `QueryPlan` (FR-022-142).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from product_inventory_query_service.domain.query_spec import Endpoint, QuerySpec, Sort
from product_inventory_query_service.domain.routes import (
    CONDUCTORS,
    INVENTORY_DRIVING_MINIMUMS,
    Conductor,
    Route,
    select_route,
)


class Evaluator(str, Enum):
    CR = "CR"
    PC = "PC"
    INVENTORY_STOCK = "INVENTORY_STOCK"
    INVENTORY_MINIMUM = "INVENTORY_MINIMUM"


@dataclass(frozen=True, slots=True)
class BatchPolicy:
    """Lotes y límite de trabajo (FR-022-133, FR-022-136); valores de la configuración."""

    minimum: int = 20
    factor: int = 2
    maximum: int = 40
    max_batches: int = 5
    work_time_seconds: float = 5.0

    def batch_size(self, page_size: int) -> int:
        return min(max(page_size * self.factor, self.minimum), self.maximum)


@dataclass(frozen=True, slots=True)
class QueryPlan:
    route: Route
    conductor: Conductor
    evaluators: tuple[Evaluator, ...]
    sort_effective: Sort
    sort_applied: str
    batch_size: int
    need: int
    max_batches: int
    work_time_seconds: float
    pairs: bool
    """`True` en bajo stock: la unidad del resultado es el par (producto, sucursal)."""


NATIVE_SORT = {
    Conductor.PC: Sort("canonical_name"),
    Conductor.INVENTORY: Sort("company_product_id"),
}
LOW_STOCK_SORT = Sort("shortfall", descending=True)
DEFAULT_CR_SORT = Sort("display_name")


def _sort(spec: QuerySpec, conductor: Conductor) -> Sort:
    if conductor is Conductor.CR:
        return spec.sort or DEFAULT_CR_SORT
    if spec.endpoint is Endpoint.LOW_STOCK_PRODUCTS:
        return LOW_STOCK_SORT
    return NATIVE_SORT[conductor]


def _evaluators(spec: QuerySpec, conductor: Conductor) -> tuple[Evaluator, ...]:
    evaluators: list[Evaluator] = []
    if conductor is not Conductor.CR:
        evaluators.append(Evaluator.CR)  # traducción de ids, adopción y filtros comerciales
    if conductor is not Conductor.PC and spec.catalog_filters:
        evaluators.append(Evaluator.PC)

    inventory_drives = conductor is Conductor.INVENTORY
    if spec.stock_state is not None and not (inventory_drives and spec.stock_state == "IN_STOCK"):
        evaluators.append(Evaluator.INVENTORY_STOCK)
    low_stock_needs_minimum = spec.endpoint is Endpoint.LOW_STOCK_PRODUCTS and not inventory_drives
    explicit_minimum = spec.minimum_state is not None and not (
        inventory_drives and spec.minimum_state in INVENTORY_DRIVING_MINIMUMS
    )
    if low_stock_needs_minimum or explicit_minimum:
        evaluators.append(Evaluator.INVENTORY_MINIMUM)
    return tuple(evaluators)


def plan(spec: QuerySpec, policy: BatchPolicy) -> QueryPlan:
    route = select_route(spec)
    conductor = CONDUCTORS[route]
    sort = _sort(spec, conductor)
    return QueryPlan(
        route=route,
        conductor=conductor,
        evaluators=_evaluators(spec, conductor),
        sort_effective=sort,
        sort_applied=sort.text,
        batch_size=policy.batch_size(spec.page_size),
        need=spec.page_size + 1,
        max_batches=policy.max_batches,
        work_time_seconds=policy.work_time_seconds,
        pairs=spec.endpoint is Endpoint.LOW_STOCK_PRODUCTS,
    )
