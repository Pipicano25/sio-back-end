"""Evaluación directa (fuerza bruta) de los filtros y del orden de cada ruta (T121; CP-130).

Recorre **todo** el juego de datos en memoria y aplica cada filtro con su definición de la spec, sin conductores,
evaluadores, lotes ni cursores. El orden es el de la ruta que elige el planificador (FR-022-65), calculado aquí
con los valores de los datos:

| Conductor | Orden |
|---|---|
| CR | (`<clave de sort>`, `company_product_id`), en la dirección pedida |
| PC | (`canonical_name` normalizado, `global_product_id`) |
| Inventory, listados | `company_product_id` |
| Inventory, bajo stock | (`shortfall` desc, `company_product_id`, `branch_id`) |
| CR, bajo stock (R-F) | orden de CR por producto y, dentro del producto, `branch_id` |
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from product_inventory_query_service.domain.planner import BatchPolicy, plan
from product_inventory_query_service.domain.query_spec import Endpoint, QuerySpec
from product_inventory_query_service.domain.routes import Conductor
from tests.oracle.dataset import Dataset, Product

ZERO = Decimal(0)


def _state(quantity: Decimal, minimum: Decimal | None) -> str:
    if minimum is None:
        return "NO_POLICY"
    return "BELOW_MINIMUM" if quantity < minimum else "AT_MINIMUM" if quantity == minimum else "ABOVE_MINIMUM"


def _matches(item: Product, spec: QuerySpec, data: Dataset, branches: list[UUID]) -> bool:
    if spec.status != "ALL" and item.status != spec.status:
        return False
    if spec.endpoint is Endpoint.INVENTORY_OVERVIEWS and not item.inventory_control_enabled:
        return False
    if spec.search:
        term = spec.search.lower()
        fields = (item.display_name, item.internal_code, *item.skus)
        if not any(term in value.lower() for value in fields):
            return False
    if spec.internal_code and item.internal_code.lower() != spec.internal_code.lower():
        return False
    if spec.sku and spec.sku.lower() not in {sku.lower() for sku in item.skus}:
        return False
    for code in (spec.barcode, spec.identifier):
        if code and code not in item.identifiers:
            return False
    if spec.brand_ids and item.brand not in spec.brand_ids:
        return False
    if spec.category_ids and not set(item.categories) & set(spec.category_ids):
        return False
    if spec.product_type and item.product_type != spec.product_type:
        return False
    if spec.has_image is not None and item.has_image != spec.has_image:
        return False
    total = sum((data.quantities.get((b, item.id), ZERO) for b in branches), ZERO)
    if spec.stock_state == "IN_STOCK" and not total > 0:
        return False
    if spec.stock_state == "OUT_OF_STOCK" and total > 0:
        return False
    if spec.minimum_state is not None:
        states = {_state(data.quantities.get((b, item.id), ZERO), data.minimums.get((b, item.id))) for b in branches}
        if spec.minimum_state not in states:
            return False
    return True


def expected(spec: QuerySpec, data: Dataset, branches: list[UUID], created_at: dict[UUID, str]) -> list:
    """Claves en el orden esperado: `company_product_id` (texto) o el par (`company_product_id`, `branch_id`)."""
    query_plan = plan(spec, BatchPolicy())
    selected = [item for item in data.products if _matches(item, spec, data, branches)]
    sort = query_plan.sort_effective

    def cr_order(items: list[Product]) -> list[Product]:
        value = {"display_name": lambda p: p.display_name, "internal_code": lambda p: p.internal_code,
                 "created_at": lambda p: created_at[p.id]}[sort.key]
        return sorted(items, key=lambda p: (value(p), str(p.id)), reverse=sort.descending)

    if spec.endpoint is Endpoint.LOW_STOCK_PRODUCTS:
        pairs = []
        for item in selected:
            for branch in branches:
                minimum = data.minimums.get((branch, item.id))
                quantity = data.quantities.get((branch, item.id), ZERO)
                if minimum is not None and quantity < minimum:
                    pairs.append((minimum - quantity, item, branch))
        if query_plan.conductor is Conductor.CR:
            position = {item.id: index for index, item in enumerate(cr_order(selected))}
            pairs.sort(key=lambda row: (position[row[1].id], str(row[2])))
        else:
            pairs.sort(key=lambda row: (-row[0], str(row[1].id), str(row[2])))
        return [(str(item.id), str(branch)) for _, item, branch in pairs]

    if query_plan.conductor is Conductor.CR:
        ordered = cr_order(selected)
    elif query_plan.conductor is Conductor.PC:
        ordered = sorted(selected, key=lambda p: (p.canonical_name.lower(), str(p.global_id)))
    else:
        ordered = sorted(selected, key=lambda p: str(p.id))
    return [str(item.id) for item in ordered]
