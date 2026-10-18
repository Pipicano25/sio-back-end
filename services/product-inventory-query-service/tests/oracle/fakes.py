"""Dobles fieles del oráculo (T120): los de `tests/fakes.py` cargados con el juego sintético.

Esos dobles ya respetan orden, `position`, `after`, `limit` y el modo evaluador de CR-1, PC-2 e INV-2, e INV-1 y
`balances/lookup` por lote; aquí solo se cargan los datos de `dataset.py` en los cuatro.
"""

from __future__ import annotations

from uuid import UUID

from product_inventory_query_service.application.ports import BranchInfo, Reference
from tests.fakes import Fakes, build_fakes
from tests.oracle.dataset import Dataset

UNIT = Reference(UUID("00000000-0000-4000-8000-0000000000aa"), "UND", "Unidad")


def load(data: Dataset) -> Fakes:
    fakes = build_fakes()
    fakes.oc.members.add(data.company)
    fakes.oc.branch_rows[data.company] = [BranchInfo(branch, data.company, "ACTIVE") for branch in data.branches]

    for item in data.products + data.foreign_globals:
        fakes.pc.add_product(item.global_id, item.canonical_name, brand_id=item.brand, has_image=item.has_image,
                             categories=set(item.categories), identifiers=set(item.identifiers), base_unit=UNIT,
                             product_type=item.product_type)

    for item in data.products:
        product = fakes.cr.add_product(
            data.company, item.display_name, id=item.id, global_product_id=item.global_id,
            internal_code=item.internal_code, status=item.status,
            inventory_control_enabled=item.inventory_control_enabled,
        )
        info = fakes.pc.add_presentation(item.global_id, "UND", "Unidad", "1")
        fakes.cr.add_presentation(product, info.id, sku=item.skus[0] if item.skus else None)
        for sku in item.skus[1:]:
            box = fakes.pc.add_presentation(item.global_id, "CJ", "Caja", "6")
            fakes.cr.add_presentation(product, box.id, sku=sku)

    for (branch, product_id), quantity in data.quantities.items():
        fakes.inventory.set_balance(data.company, branch, product_id, str(quantity))
    for (branch, product_id), minimum in data.minimums.items():
        fakes.inventory.set_policy(data.company, branch, product_id, str(minimum))
    return fakes
