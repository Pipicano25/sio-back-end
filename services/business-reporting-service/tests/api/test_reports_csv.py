"""CSV de los cuatro reportes (spec 023, FR-023-40 a FR-023-46; `contracts/csv.md`).

Garantías verificadas: mismos datos que el JSON, UTF-8 con BOM, protección de fórmulas, fila final `TOTAL FILAS`
solo si todo se leyó, errores antes del primer byte como RFC 9457, error a mitad con la línea `#ERROR` y sin
totales, máximo de filas y memoria acotada (las páginas se piden de una en una).
"""

from __future__ import annotations

import csv
import io

import pytest

from tests.api.support import PERIOD, base, branch_base, seed_evolution, seed_purchases, seed_sales
from tests.fakes import TABLET


def rows_of(text: str) -> list[list[str]]:
    assert text.startswith("﻿"), "falta el BOM UTF-8"
    return list(csv.reader(io.StringIO(text[1:])))


def get_csv(client, url: str, **params):
    response = client.get(url, params={**PERIOD, "format": "csv", **params})
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    return response


def test_top_products_csv_matches_json(as_user, fakes) -> None:
    seed_sales(fakes)
    client = as_user("reportes.test")
    data = client.get(f"{base(fakes)}/top-selling-products", params=PERIOD).json()
    response = get_csv(client, f"{base(fakes)}/top-selling-products")
    assert response.headers["content-disposition"] == (
        f'attachment; filename="top-selling-products-{fakes.company.id}-2026-10-01-2026-10-18.csv"')
    rows = rows_of(response.text)
    assert rows[0] == ["Puesto", "Código", "Producto", "Unidad base", "Cantidad (unidad base)", "Importe", "Moneda",
                       "Ventas", "ID producto"]
    body = rows[1:1 + len(data["items"])]
    assert [[r[0], r[1], r[4], r[5], r[8]] for r in body] == [
        [str(i["rank"]), i["product_code"], i["quantity_base"], i["amount"], i["company_product_id"]] for i in data["items"]]
    assert rows[-2][:1] == ["TOTAL"] and rows[-2][5] == "1025000.00"
    assert rows[-1] == ["TOTAL FILAS", str(len(data["items"]))]


def test_sales_by_branch_and_purchases_csv_match_json(as_user, fakes) -> None:
    seed_sales(fakes)
    seed_purchases(fakes, 3)
    client = as_user("reportes.test")
    branches = client.get(f"{base(fakes)}/sales-by-branch", params=PERIOD).json()
    rows = rows_of(get_csv(client, f"{base(fakes)}/sales-by-branch").text)
    assert [[r[0], r[4], r[5]] for r in rows[1:3]] == [
        [i["branch_code"], i["total_amount"], i["share_percentage"]] for i in branches["items"]]
    purchases = client.get(f"{base(fakes)}/purchases", params=PERIOD).json()
    rows = rows_of(get_csv(client, f"{base(fakes)}/purchases").text)
    assert [[r[5], r[8], r[10]] for r in rows[1:4]] == [[i["number"], i["category"], i["total"]] for i in purchases["items"]]
    labels = [r[0] for r in rows[4:]]
    assert labels == ["TOTAL RECIBIDAS", "TOTAL PENDIENTES DE RECEPCIÓN", "TOTAL ANULADAS (no suma)", "TOTAL EFECTIVO",
                      "TOTAL FILAS"]
    assert rows[7][10] == "2000.00" and rows[-1] == ["TOTAL FILAS", "3"]


def test_csv_walks_all_pages_one_at_a_time(as_user, fakes) -> None:
    seed_purchases(fakes, 250)
    rows = rows_of(get_csv(as_user("reportes.test"), f"{base(fakes)}/purchases", page_size="10").text)
    assert rows[-1] == ["TOTAL FILAS", "250"]
    pages = [args["page"] for name, args in fakes.log.calls if name == "purchase_period"]
    sizes = {args["page_size"] for name, args in fakes.log.calls if name == "purchase_period"}
    assert pages == [1, 2, 3] and sizes == {100}  # el CSV ignora `page_size` y pide páginas de 100


def test_stock_evolution_csv_matches_json_without_costs(as_user, fakes) -> None:
    seed_evolution(fakes, 120)
    client = as_user("inventario.test")
    rows = rows_of(get_csv(client, f"{branch_base(fakes)}/stock-evolution").text)
    assert rows[0][3:12] == ["Existencia inicial", "Entradas", "Salidas", "Reversos de entrada", "Reversos de salida",
                             "Ajustes positivos", "Ajustes negativos", "Existencia final", "Movimientos"]
    assert not any("costo" in h.lower() or "valor" in h.lower() for h in rows[0])
    assert len(rows) == 1 + 120 + 1 and rows[-1] == ["TOTAL FILAS", "120"]
    first = client.get(f"{branch_base(fakes)}/stock-evolution", params={**PERIOD, "page_size": "1"}).json()["items"][0]
    assert rows[1][:12] == [first["product_code"], first["product_name"], "TAB", first["opening_quantity"],
                            first["entries"], first["outputs"], first["entry_reversals"], first["output_reversals"],
                            first["positive_adjustments"], first["negative_adjustments"], first["closing_quantity"],
                            str(first["movement_count"])]


@pytest.mark.parametrize("name", ["=HYPERLINK(\"http://x\")", "+1", "-2", "@SUM(A1)", "\tTAB", "\rCR"])
def test_formula_injection_is_neutralized_in_text_cells(as_user, fakes, name) -> None:
    product = fakes.product(name, code=name, unit=TABLET)
    from business_reporting_service.application.ports import ProductSales, SalesTotal
    from tests.fakes import D

    fakes.product_sales = [ProductSales(product, name, name, "COP", D("1"), D("-5"), 1, [])]
    fakes.sales_totals = [SalesTotal("COP", D("-5"), 1)]
    rows = rows_of(get_csv(as_user("reportes.test"), f"{base(fakes)}/top-selling-products").text)
    assert rows[1][1] == "'" + name and rows[1][2] == "'" + name
    assert rows[1][5] == "-5.00"  # los números negativos no se alteran


def test_bom_can_be_disabled(as_user, fakes) -> None:
    seed_sales(fakes)
    response = as_user("reportes.test").get(f"{base(fakes)}/top-selling-products",
                                            params={**PERIOD, "format": "csv", "bom": "false"})
    assert not response.text.startswith("﻿") and response.text.startswith("Puesto,")


def test_error_before_the_first_byte_is_a_problem_response(as_user, fakes) -> None:
    seed_purchases(fakes, 5)
    fakes.fail.add("purchase_period")
    response = as_user("reportes.test").get(f"{base(fakes)}/purchases", params={**PERIOD, "format": "csv"})
    assert response.status_code == 503
    assert response.headers["content-type"].startswith("application/problem+json")


def test_error_in_the_middle_ends_with_error_line_and_no_totals() -> None:
    """Página 2 falla: filas de la página 1, línea `#ERROR` (otra cantidad de columnas), sin totales ni `TOTAL FILAS`,
    y la excepción se relanza (con Uvicorn, la conexión termina sin el bloque final: `test_csv_connection.py`)."""
    import asyncio

    from business_reporting_service.api.csv_stream import CsvPlan, Number, stream

    async def pages():
        yield [["b", Number(2)]]
        raise RuntimeError("fallo de la página 3")

    plan = CsvPlan(header=["Columna", "Valor"], first_rows=[["a", Number(1)]], next_pages=pages,
                   totals=lambda: [["TOTAL", Number(3)]])

    async def collect():
        chunks = []
        with pytest.raises(RuntimeError):
            async for chunk in stream(plan):
                chunks.append(chunk)
        return "".join(chunks)

    text = asyncio.run(collect())
    lines = text.lstrip("\ufeff").rstrip("\r\n").split("\r\n")
    assert lines[:3] == ["Columna,Valor", "a,1", "b,2"]
    assert lines[-1].startswith("#ERROR: reporte incompleto, trace_id=")
    assert "TOTAL" not in text  # ni los totales del reporte ni la fila de completitud


def test_too_many_rows_is_422_before_streaming(as_user, fakes, test_settings) -> None:
    from dataclasses import replace

    seed_purchases(fakes, 120)
    client = as_user("reportes.test")
    client._client.app.state.settings = replace(test_settings, csv_max_rows=100)
    response = client.get(f"{base(fakes)}/purchases", params={**PERIOD, "format": "csv"})
    assert response.status_code == 422 and response.json()["errors"][0]["code"] == "CSV_TOO_LARGE"
