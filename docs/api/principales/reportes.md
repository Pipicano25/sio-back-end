# 6.9 Reportes

[← API principales](README.md) · [← Índice](../index.md)

Información de negocio consolidada para dueños, administradores y supervisores: qué se vende más, cuánto vende cada sucursal, qué se compró en el período y cómo evolucionaron las existencias. Todos los reportes son de solo lectura, se calculan sobre documentos confirmados y se entregan en JSON o CSV.

Servicio propietario: [Business Reporting](../servicios/business-reporting.md), base `https://sio-business-reporting-dev.onrender.com/api/v1`. Las consultas operativas de inventario (existencias actuales, bajo mínimo, indicadores) están en [Inventario §1–4](inventario.md#1-buscar-productos-con-precio-y-existencias) y no se repiten aquí.

| # | Funcionalidad | Método y ruta | Permiso (`perm:business-reporting:…`) | Ficha |
|---|---|---|---|---|
| 1 | Productos más vendidos de la empresa | `GET /companies/{company_id}/reports/top-selling-products` | `top_selling_products:read` | [BR 3](../servicios/business-reporting.md#3-get-companiescompany_idreportstop-selling-products) |
| 2 | Productos más vendidos de una sucursal | `GET /companies/{company_id}/branches/{branch_id}/reports/top-selling-products` | `top_selling_products:read` | [BR 4](../servicios/business-reporting.md#4-get-companiescompany_idbranchesbranch_idreportstop-selling-products) |
| 3 | Ventas por sucursal (comparativo) | `GET /companies/{company_id}/reports/sales-by-branch` | `sales_by_branch:read` | [BR 5](../servicios/business-reporting.md#5-get-companiescompany_idreportssales-by-branch) |
| 4 | Ventas de una sucursal | `GET /companies/{company_id}/branches/{branch_id}/reports/sales-by-branch` | `sales_by_branch:read` | [BR 6](../servicios/business-reporting.md#6-get-companiescompany_idbranchesbranch_idreportssales-by-branch) |
| 5 | Compras del período de la empresa | `GET /companies/{company_id}/reports/purchases` | `purchases:read` | [BR 7](../servicios/business-reporting.md#7-get-companiescompany_idreportspurchases) |
| 6 | Compras del período de una sucursal | `GET /companies/{company_id}/branches/{branch_id}/reports/purchases` | `purchases:read` | [BR 8](../servicios/business-reporting.md#8-get-companiescompany_idbranchesbranch_idreportspurchases) |
| 7 | Evolución de existencias consolidada | `GET /companies/{company_id}/reports/stock-evolution` | `stock_evolution:read` | [BR 9](../servicios/business-reporting.md#9-get-companiescompany_idreportsstock-evolution) |
| 8 | Evolución de existencias de una sucursal | `GET /companies/{company_id}/branches/{branch_id}/reports/stock-evolution` | `stock_evolution:read` | [BR 10](../servicios/business-reporting.md#10-get-companiescompany_idbranchesbranch_idreportsstock-evolution) |
| 9 | Indicadores operativos de inventario | `GET /api/v1/companies/{company_id}/inventory-summary` (Product Inventory Query) | `perm:product-inventory-query:inventory_summary:read` | [Inventario §4](inventario.md#4-indicadores-de-inventario) |
| 10 | Productos bajo el mínimo | `GET /api/v1/companies/{company_id}/low-stock-products` (Product Inventory Query) | `perm:product-inventory-query:low_stock_products:read` | [Inventario §3](inventario.md#3-productos-bajo-el-mínimo) |

Business Reporting obtiene los datos de las agregaciones de solo lectura de Sales (`GET …/sales-aggregates/by-product`, `…/by-branch`; Sales 22, 23), Purchase (`GET …/purchase-reports/period`; Purchase 24) e Inventory (`GET …/stock-evolution`; Inventory 37, 38). Esas agregaciones son **llamadas internas con cuenta técnica**; el frontend consume los reportes de esta sección, no las agregaciones.

---

## Parámetros comunes

| Parámetro | Tipo | Obligatorio | Significado |
|---|---|---|---|
| `date_from`, `date_to` | fecha `YYYY-MM-DD` | Sí | Período inclusivo, en la zona horaria de la empresa |
| `format` | `json` (por defecto) o `csv` | No | Con `csv` la respuesta es `text/csv` descargable (`Content-Disposition: attachment`) |
| `bom` | boolean (por defecto `true`) | No | Solo con `csv`: antepone la marca BOM para que Excel abra el archivo en UTF-8 |
| `branch_id[]` | UUID repetible (≤ 100) | No | Limita la variante de empresa a algunas sucursales; la variante `/branches/{branch_id}/…` siempre es de una sola |

Todas exigen membresía `ACTIVE` en la empresa; las variantes por sucursal exigen que la sucursal sea de la empresa (`404` en caso contrario). Respuesta JSON común: `report` (nombre), `company_id`, `date_from`, `date_to`, `generated_at`, `criteria` (`status: CONFIRMED`), `branch_ids[]`, `items[]`, `totals[]` por moneda. Si una fuente no responde, `503 DEPENDENCY_UNAVAILABLE`; si el período es inválido, `422 VALIDATION_ERROR`.

## 1 y 2. Productos más vendidos

**¿Qué información entrega?** El ranking de productos por cantidad vendida (en unidad base) o por monto, con número de ventas y, opcionalmente, el desglose por presentación. Sirve para decidir compras, promociones y espacio en estantería.

**¿Qué API debe consumir el frontend?** `GET https://sio-business-reporting-dev.onrender.com/api/v1/companies/{company_id}/reports/top-selling-products?date_from=2026-10-01&date_to=2026-10-31&rank_by=amount&limit=20&include_presentations=true` o la variante `…/branches/{branch_id}/reports/top-selling-products`. Permiso `perm:business-reporting:top_selling_products:read`. Parámetros propios: `rank_by` (`quantity` por defecto, `amount`), `limit` (1–100, por defecto 20), `include_presentations`.

```bash
curl -sS 'https://sio-business-reporting-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/reports/top-selling-products?date_from=2026-10-01&date_to=2026-10-31&rank_by=amount&limit=10' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**¿Cómo sabe que funcionó?** `200` con `items[]`: `rank`, `company_product_id`, `product_code`, `product_name`, `base_unit`, `quantity_base`, `currency_code`, `amount`, `sales_count` y `presentations[]` si se pidió; `totals[]` por moneda; `mixed_base_units` avisa cuando el ranking por cantidad mezcla unidades base distintas (compara por `amount` en ese caso).

## 3 y 4. Ventas por sucursal

**¿Qué información entrega?** Número de ventas, monto total y participación porcentual de cada sucursal en el período; la variante por sucursal devuelve solo la suya.

**¿Qué API debe consumir el frontend?** `GET https://sio-business-reporting-dev.onrender.com/api/v1/companies/{company_id}/reports/sales-by-branch?date_from=…&date_to=…` (permiso `perm:business-reporting:sales_by_branch:read`) o `…/branches/{branch_id}/reports/sales-by-branch`.

**¿Cómo sabe que funcionó?** `200` con `items[]`: `branch_id`, `branch_code`, `branch_name`, `currency_code`, `sales_count`, `total_amount`, `share_percentage`; `totals[]` por moneda. Solo cuenta ventas `CONFIRMED` (las anuladas no suman).

## 5 y 6. Compras del período

**¿Qué información entrega?** Las compras del período, una fila por compra, clasificadas en `RECEIVED` (ya en inventario), `PENDING_RECEIPT` (confirmadas sin recibir) y `CANCELLED`, con totales por categoría y el total efectivo. Sirve para seguimiento de proveedores y de mercancía pendiente.

**¿Qué API debe consumir el frontend?** `GET https://sio-business-reporting-dev.onrender.com/api/v1/companies/{company_id}/reports/purchases?date_from=…&date_to=…&category=PENDING_RECEIPT` (permiso `perm:business-reporting:purchases:read`) o la variante por sucursal. Parámetros propios: `category[]`, `page`, `page_size` (1–100, por defecto 50).

**¿Cómo sabe que funcionó?** `200` con `items[]`: `purchase_id`, `operation_date`, `received_at`, `branch_name`, `supplier_name`, `supplier_identification`, `number`, `supplier_document_number`, `status`, `category`, `receipt_status`, `currency_code`, `total`; `totals[]` con `received_total`, `pending_receipt_total`, `cancelled_total`, `effective_total` y sus conteos; paginación `page`, `page_size`, `total_records`, `total_pages`. Para abrir una compra desde la fila usa `purchase_id` ([Compras §8](compras.md#8-consultar-la-compra-con-impuestos-y-totales)).

## 7 y 8. Evolución de existencias

**¿Qué información entrega?** Por producto, la existencia inicial del período, las entradas, salidas, reversos y ajustes, y la existencia final, consolidada en la empresa o en una sucursal. Permite explicar cómo se llegó al saldo actual.

**¿Qué API debe consumir el frontend?** `GET https://sio-business-reporting-dev.onrender.com/api/v1/companies/{company_id}/reports/stock-evolution?date_from=…&date_to=…&company_product_id=…` (permiso `perm:business-reporting:stock_evolution:read`) o `…/branches/{branch_id}/reports/stock-evolution`. Parámetros propios: `company_product_id[]` (≤ 100), `page`, `page_size`.

**¿Cómo sabe que funcionó?** `200` con `timezone` e `items[]`: `company_product_id`, `product_code`, `product_name`, `base_unit`, `opening_quantity`, `entries`, `outputs`, `entry_reversals`, `output_reversals`, `positive_adjustments`, `negative_adjustments`, `closing_quantity`, `movement_count`, `branch_count`. Se cumple `closing = opening + entries − outputs − entry_reversals + output_reversals + positive_adjustments − negative_adjustments`. El detalle movimiento a movimiento está en el kardex ([Inventario §6](inventario.md#6-kardex-de-un-producto)).

## 9 y 10. Indicadores e inventario bajo mínimo

Son operaciones de Product Inventory Query descritas en [Inventario](inventario.md): el resumen (`inventory-summary`) da los contadores del tablero y `low-stock-products` la lista accionable de reposición. Se mencionan aquí porque completan la vista gerencial, pero su ficha es una sola.

## Exportar a CSV

Cualquier reporte de Business Reporting acepta `format=csv`:

```bash
curl -sS 'https://sio-business-reporting-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/reports/sales-by-branch?date_from=2026-10-01&date_to=2026-10-31&format=csv' \
  -H "Authorization: Bearer $ACCESS_TOKEN" -o ventas-por-sucursal.csv
```

La respuesta es `200 text/csv` con nombre de archivo sugerido en `Content-Disposition`; con `bom=false` se omite la marca de orden de bytes.

## Dependencias con otros módulos

- [Ventas](ventas.md) y [Compras](compras.md) producen los documentos confirmados que alimentan los reportes 1–6.
- [Inventario](inventario.md) produce los movimientos de los reportes 7–8 y las consultas 9–10.
- [Administración empresarial](administracion-empresarial.md): los nombres de sucursal de los reportes salen de Operational Context.
