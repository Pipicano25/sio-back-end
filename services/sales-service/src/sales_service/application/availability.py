"""Disponibilidad de existencias de una venta (Historia 4; FR-013, FR-015; research.md R-08).

Requerido por producto = suma de `quantity × factor` de sus líneas (unidad base, 4
decimales); disponible = saldo de la sucursal en Inventory (`balances/lookup`, identidad
técnica). **No reserva**: es informativa y anticipa el rechazo; la barrera definitiva contra
el saldo insuficiente es Inventory al aplicar la salida (RC-04).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID

from sales_service.application.exceptions import NotFoundError
from sales_service.application.ports import BalanceInfo, InventoryGateway
from sales_service.application.snapshots import line_base_quantity
from sales_service.domain.money import QUANTITY_QUANTUM
from sales_service.infrastructure.models import Sale, SaleDetail
from sales_service.infrastructure.repository import SaleRepository


@dataclass
class ProductAvailability:
    company_product_id: UUID
    line_numbers: list[int] = field(default_factory=list)
    required_base_quantity: Decimal = Decimal("0")
    available_base_quantity: Decimal = Decimal("0")

    @property
    def is_available(self) -> bool:
        return self.available_base_quantity >= self.required_base_quantity


def required_by_product(lines: Sequence[SaleDetail]) -> dict[UUID, ProductAvailability]:
    products: dict[UUID, ProductAvailability] = {}
    for line in lines:
        entry = products.setdefault(line.company_product_id, ProductAvailability(line.company_product_id))
        entry.line_numbers.append(line.line_number)
        entry.required_base_quantity += line_base_quantity(line)
    return products


def summarize(lines: Sequence[SaleDetail], balances: dict[UUID, BalanceInfo]) -> list[ProductAvailability]:
    products = required_by_product(lines)
    for product_id, entry in products.items():
        balance = balances.get(product_id)
        entry.available_base_quantity = (balance.quantity if balance else Decimal("0")).quantize(QUANTITY_QUANTUM)
        entry.required_base_quantity = entry.required_base_quantity.quantize(QUANTITY_QUANTUM)
    return list(products.values())


def check_lines(
    inventory: InventoryGateway, company_id: UUID, branch_id: UUID, lines: Sequence[SaleDetail]
) -> list[ProductAvailability]:
    """Consulta los saldos de los productos de las líneas y devuelve el resumen por producto."""
    product_ids = list(dict.fromkeys(line.company_product_id for line in lines))
    balances = inventory.lookup_balances(company_id, branch_id, product_ids) if product_ids else {}
    return summarize(lines, balances)


def shortages(rows: Sequence[ProductAvailability]) -> list[dict]:
    """Faltantes para `409 INSUFFICIENT_STOCK` (mismo formato que los traducidos de Inventory)."""
    return [
        {
            "line_numbers": list(row.line_numbers),
            "company_product_id": str(row.company_product_id),
            "available": format(row.available_base_quantity, "f"),
            "requested": format(row.required_base_quantity, "f"),
        }
        for row in rows
        if not row.is_available
    ]


class AvailabilityService:
    def __init__(self, repository: SaleRepository, inventory: InventoryGateway) -> None:
        self._repo = repository
        self._inventory = inventory

    def availability(self, company_id: UUID, sale_id: UUID) -> tuple[Sale, list[ProductAvailability]]:
        sale = self._repo.get_sale(company_id, sale_id)
        if sale is None:
            raise NotFoundError()
        lines = self._repo.lines(sale.id)
        self._repo.end_read()
        return sale, check_lines(self._inventory, company_id, sale.branch_id, lines)
