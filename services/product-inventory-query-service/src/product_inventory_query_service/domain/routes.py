"""Rutas del planificador (FR-022-132), como lista ordenada de reglas: gana la primera que se cumple.

R-F se evalúa antes que las demás: un `sort` explícito por un campo de CR en una ruta que no conduce CR hace que
CR conduzca (D-022-6, opción A).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

from product_inventory_query_service.domain.query_spec import Endpoint, QuerySpec


class Route(str, Enum):
    R_F = "R-F"
    R_A1 = "R-A1"
    R_A2 = "R-A2"
    R_B = "R-B"
    R_C = "R-C"
    R_D = "R-D"
    R_E = "R-E"


class Conductor(str, Enum):
    CR = "CR"
    PC = "PC"
    INVENTORY = "INVENTORY"


INVENTORY_DRIVING_MINIMUMS = {"BELOW_MINIMUM", "AT_MINIMUM", "ABOVE_MINIMUM"}
"""Estados frente al mínimo que INV-2 puede conducir; `NO_POLICY` no (esos productos no existen en Inventory)."""


def drives_inventory(spec: QuerySpec) -> bool:
    if spec.endpoint is Endpoint.LOW_STOCK_PRODUCTS:
        return True
    return spec.stock_state == "IN_STOCK" or spec.minimum_state in INVENTORY_DRIVING_MINIMUMS


@dataclass(frozen=True, slots=True)
class Rule:
    route: Route
    conductor: Conductor
    applies: Callable[[QuerySpec], bool]


def _native_route(spec: QuerySpec) -> Route:
    for rule in NATIVE_RULES:
        if rule.applies(spec):
            return rule.route
    raise AssertionError("R-E siempre se cumple")  # pragma: no cover


NATIVE_RULES: tuple[Rule, ...] = (
    Rule(Route.R_A1, Conductor.PC, lambda s: bool(s.barcode or s.identifier)),
    Rule(Route.R_A2, Conductor.CR, lambda s: bool(s.internal_code or s.sku)),
    Rule(Route.R_B, Conductor.CR, lambda s: s.search is not None),
    Rule(Route.R_C, Conductor.PC, lambda s: s.catalog_filters),
    Rule(Route.R_D, Conductor.INVENTORY, drives_inventory),
    Rule(Route.R_E, Conductor.CR, lambda s: True),
)

CONDUCTORS = {rule.route: rule.conductor for rule in NATIVE_RULES} | {Route.R_F: Conductor.CR}


def select_route(spec: QuerySpec) -> Route:
    """`low-stock-products` siempre usa R-D (pares de INV-2) salvo `sort` explícito (R-F); los demás filtros se
    evalúan sobre los pares (FR-022-132)."""
    if spec.endpoint is Endpoint.LOW_STOCK_PRODUCTS:
        return Route.R_F if spec.sort is not None else Route.R_D
    native = _native_route(spec)
    if spec.sort is not None and CONDUCTORS[native] is not Conductor.CR:
        return Route.R_F
    return native
