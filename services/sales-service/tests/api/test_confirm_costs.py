"""Costo FIFO y margen al confirmar (FR-019, P-01, P-05, C-03, DS-06; research.md R-10; T053)."""

from __future__ import annotations

import logging

from tests.conftest import base, fetch, line


def lines_of(supervisor, world, sale):
    return supervisor.get(f"{base(world)}/sales/{sale['id']}").json()


def outcomes(caplog) -> list[str]:
    """Motivo del porcentaje por línea, del log estructurado de la confirmación (P-01)."""
    records = [record.getMessage() for record in caplog.records if "sales.margin.percentage_outcome" in record.getMessage()]
    assert len(records) == 1  # una línea por venta
    return [item.split(":", 1)[1] for item in records[0].rsplit("resultados=", 1)[1].split(",")]


def test_fifo_across_layers_is_copied_without_recalculation(supervisor, world, fakes, make_sequence, make_draft, confirm, caplog) -> None:
    make_sequence()
    fakes.inventory.layers.clear()
    fakes.inventory.stock(world.branch, world.product, "10", "1000")
    fakes.inventory.stock(world.branch, world.product, "10", "1333.3333")
    draft = make_draft(line(world.product, "15"))  # 15 × 1500 = 22500
    with caplog.at_level(logging.INFO, logger="sales_service"):
        assert confirm(draft).status_code == 200
    detail = lines_of(supervisor, world, draft)["lines"][0]
    # Inventory: 10 × 1000 + 5 × 1333.3333 = 16666.6665 → unit_cost 1111.1111 (por unidad base)
    assert detail["unit_cost_snapshot"] == "1111.1111"
    assert detail["cost_total"] == "16666.67"  # movement_value redondeado a 2 decimales
    assert detail["cost_known"] is True
    assert detail["gross_margin_amount"] == "5833.33"  # 22500 − 16666.67
    assert detail["gross_margin_percentage"] == "25.9259"
    assert outcomes(caplog) == ["COMPUTED"]


def test_unknown_cost_confirms_with_null_margins(supervisor, world, fakes, make_sequence, make_draft, confirm, test_engine, caplog) -> None:
    """C-03: unidades de apertura sin costo histórico → se confirma; márgenes nulos; indicador en la cabecera."""
    make_sequence()
    fakes.inventory.layers.clear()
    fakes.inventory.stock(world.branch, world.product, "5", "0", known=False)
    fakes.inventory.stock(world.branch, world.product_2, "5", "6000")
    draft = make_draft(line(world.product, "2"), line(world.product_2, "1"))
    with caplog.at_level(logging.INFO, logger="sales_service"):
        response = confirm(draft)
    assert response.status_code == 200, response.text
    seen = lines_of(supervisor, world, draft)
    unknown, known = seen["lines"]
    assert (unknown["cost_known"], unknown["gross_margin_amount"], unknown["gross_margin_percentage"]) == (False, None, None)
    assert unknown["cost_total"] == "0.00" and unknown["unit_cost_snapshot"] == "0.0000"
    assert known["cost_known"] is True and known["gross_margin_percentage"] == "33.3333"
    assert seen["has_unknown_cost"] is True
    assert outcomes(caplog) == ["COST_UNKNOWN", "COMPUTED"]
    row = fetch(test_engine, "SELECT has_unknown_cost FROM sales")[0]
    assert row["has_unknown_cost"] is True


def test_net_zero_keeps_amount_and_leaves_percentage_null(supervisor, world, make_sequence, make_draft, confirm, caplog) -> None:
    """P-01: descuento total → margen = −costo; porcentaje no definido."""
    make_sequence()
    draft = make_draft(line(world.product, "2", discount_amount="3000"))
    with caplog.at_level(logging.INFO, logger="sales_service"):
        assert confirm(draft).status_code == 200
    detail = lines_of(supervisor, world, draft)["lines"][0]
    assert (detail["gross_margin_amount"], detail["gross_margin_percentage"]) == ("-2000.00", None)
    assert outcomes(caplog) == ["NET_ZERO"]


def test_out_of_range_percentage_is_null_never_saturated(supervisor, world, fakes, make_sequence, make_draft, confirm, caplog) -> None:
    """P-01: margen tan negativo que el porcentaje no cabe en NUMERIC(7,4) → nulo; el monto se guarda."""
    make_sequence()
    fakes.cr.set_unit_price(world.product, "1.00")
    fakes.inventory.layers.clear()
    fakes.inventory.stock(world.branch, world.product, "5", "5000")
    draft = make_draft(line(world.product, "1"))
    with caplog.at_level(logging.INFO, logger="sales_service"):
        assert confirm(draft).status_code == 200
    detail = lines_of(supervisor, world, draft)["lines"][0]
    assert (detail["gross_margin_amount"], detail["gross_margin_percentage"]) == ("-4999.00", None)
    assert outcomes(caplog) == ["OUT_OF_RANGE"]


def test_selling_below_cost_is_allowed_with_negative_margin(supervisor, world, fakes, make_sequence, make_draft, confirm) -> None:
    make_sequence()
    fakes.inventory.layers.clear()
    fakes.inventory.stock(world.branch, world.product, "5", "2000")
    draft = make_draft(line(world.product, "1"))
    assert confirm(draft).status_code == 200
    detail = lines_of(supervisor, world, draft)["lines"][0]
    assert (detail["gross_margin_amount"], detail["gross_margin_percentage"]) == ("-500.00", "-33.3333")


def test_presentation_line_cost_is_per_base_unit(supervisor, world, fakes, make_sequence, make_draft, confirm) -> None:
    """P-05: la línea vende cajas, pero `unit_cost_snapshot` es el costo por unidad base que informa Inventory."""
    make_sequence()
    draft = make_draft(line(world.product, "1", company_product_presentation_id=world.presentation))
    assert confirm(draft).status_code == 200
    detail = lines_of(supervisor, world, draft)["lines"][0]
    assert detail["unit_price"] == "18000.0000" and detail["unit_cost_snapshot"] == "1000.0000"
    assert detail["cost_total"] == "12000.00" and detail["gross_margin_amount"] == "6000.00"
