"""El contrato de entrada hacia Inventory no cambia con la spec 021 (T016; CP-T12; RC-021-4).

La solicitud que Purchase envía a Inventory al recibir es idéntica a la de la spec 020: cantidad en unidad base y
costo por unidad base **sin** impuesto (`(subtotal − descuento) / cantidad base`, 4 decimales). La tasa de impuesto de
la línea (spec 021) no aparece en la solicitud ni altera el costo. Datos ficticios; el 19 % no es una tarifa real.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from purchase_service.application.operation_engine import OperationEngine
from purchase_service.infrastructure.models import Purchase, PurchaseDetail, PurchaseOperation

COMPANY = UUID("00000000-0000-0000-0000-0000000000c1")
BRANCH = UUID("00000000-0000-0000-0000-0000000000b1")
PURCHASE = UUID("00000000-0000-0000-0000-0000000000f1")
OPERATION = UUID("00000000-0000-0000-0000-0000000000a1")
CORRELATION = UUID("00000000-0000-0000-0000-0000000000a2")
LINE_1 = UUID("00000000-0000-0000-0000-0000000000d1")
LINE_2 = UUID("00000000-0000-0000-0000-0000000000d2")
PRODUCT = UUID("00000000-0000-0000-0000-0000000000e1")


class _Lines:
    def __init__(self, lines: list[PurchaseDetail]) -> None:
        self._lines = lines

    def lines(self, purchase_id: UUID) -> list[PurchaseDetail]:
        assert purchase_id == PURCHASE
        return self._lines


def _line(line_id: UUID, factor: str, tax_percentage: str | None) -> PurchaseDetail:
    return PurchaseDetail(
        id=line_id,
        purchase_id=PURCHASE,
        company_product_id=PRODUCT,
        quantity=Decimal("10.0000"),
        unit_cost=Decimal("2000.0000"),
        discount_amount=Decimal("0.00"),
        tax_amount=Decimal("3800.00"),
        subtotal=Decimal("20000.00"),
        total=Decimal("23800.00"),
        base_quantity_factor_snapshot=Decimal(factor),
        tax_percentage=Decimal(tax_percentage) if tax_percentage else None,
        tax_percentage_source="PRODUCT_DEFAULT" if tax_percentage else None,
    )


def test_entry_payload_is_identical_to_spec_020() -> None:
    lines = [_line(LINE_1, "1", "19"), _line(LINE_2, "453.59237", None)]
    engine = OperationEngine(_Lines(lines), inventory=None, clock=lambda: None)  # type: ignore[arg-type]
    purchase = Purchase(id=PURCHASE, company_id=COMPANY, branch_id=BRANCH)
    operation = PurchaseOperation(id=OPERATION, correlation_id=CORRELATION)

    payload = engine.entry_payload(purchase, operation, "application-user")

    assert payload == {
        "operation_key": str(OPERATION),
        "company_id": str(COMPANY),
        "branch_id": str(BRANCH),
        "origin_type": "PURCHASE",
        "origin_id": str(PURCHASE),
        "application_user_id": "application-user",
        "correlation_id": str(CORRELATION),
        "reason": None,
        "lines": [
            # Factor 1: 10 unidades a 2.000 (sin los 3.800 de impuesto).
            {"origin_detail_id": str(LINE_1), "company_product_id": str(PRODUCT), "quantity": "10.0000", "unit_cost": "2000.0000"},
            # Unidad base gramo: 4.535,9237 g a 20.000 / 4.535,9237 = 4,4092 (4 decimales, sin impuesto).
            {"origin_detail_id": str(LINE_2), "company_product_id": str(PRODUCT), "quantity": "4535.9237", "unit_cost": "4.4092"},
        ],
    }
    assert all("tax" not in key for line in payload["lines"] for key in line)
