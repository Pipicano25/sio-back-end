# Consultar inventario

[← Flujos](README.md) · [← Índice](../index.md) · Fichas: [Product Inventory Query](../servicios/product-inventory-query.md), [Inventory](../servicios/inventory.md)

Tres pantallas típicas de solo lectura y cómo resolverlas con la menor cantidad de llamadas. Perfil típico: grupo `inventario` (ve existencias y mínimos; no ve precios) o `ventas` (ve precios y existencias; no ve mínimos).

## 1. Contexto operativo

`GET https://sio-operational-context-dev.onrender.com/api/v1/me/operational-context` → [company_id](../parametros/company-id.md) y las sucursales del usuario ([branch_id](../parametros/branch-id.md)). Para las consultas de Inventory y Product Inventory Query basta la membresía en la empresa: no hace falta tener asignada la sucursal.

## 2. Catálogo con existencias (una sola llamada)

`GET https://sio-product-inventory-query-dev.onrender.com/api/v1/companies/{company_id}/inventory-overviews?status=ACTIVE&page_size=20` ([operación 5](../servicios/product-inventory-query.md#5-get-companiescompany_idinventory-overviews)); permiso `perm:product-inventory-query:inventory_overviews:read` (+ `perm:product-inventory-query:stock:read` para `stock`, `perm:inventory:product-policies:read` para mínimos).

- Filtros útiles: `search`, `barcode`, `category_id` con `include_descendants=true`, `stock_state=OUT_OF_STOCK`, `minimum_state=BELOW_MINIMUM`, `branch_id` (repetible).
- Paginación por cursor: enviar `cursor=<next_cursor>` con los mismos filtros; si `pagination_reset` es `true`, reiniciar la lista; si `partial` es `true`, seguir pidiendo.
- Por sucursal: `…/companies/{company_id}/branches/{branch_id}/inventory-overviews`.

## 3. Productos bajo mínimo

`GET https://sio-product-inventory-query-dev.onrender.com/api/v1/companies/{company_id}/low-stock-products` ([operación 7](../servicios/product-inventory-query.md#7-get-companiescompany_idlow-stock-products)); exige `perm:product-inventory-query:low_stock_products:read`, `perm:product-inventory-query:stock:read` y `perm:inventory:product-policies:read`. Devuelve pares producto–sucursal con `shortfall` (faltante), ordenados por faltante descendente.

Indicadores para un tablero: `GET …/companies/{company_id}/inventory-summary` ([operación 9](../servicios/product-inventory-query.md#9-get-companiescompany_idinventory-summary)): productos adoptados, con saldo, con política y bajo mínimo, por sucursal y consolidados.

## 4. Detalle de un producto en una sucursal (Inventory)

- Saldo: `GET https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/branches/{branch_id}/balances/{company_product_id}` ([Inventory, operación 8](../servicios/inventory.md#8-get-companiescompany_idbranchesbranch_idbalancescompany_product_id)); permiso `perm:inventory:balances:read`. Devuelve `quantity` en unidad base, `inventory_value` y `average_unit_cost`.
- Kardex: `GET …/branches/{branch_id}/kardex/{company_product_id}?occurred_at_from=2026-10-01T00:00:00Z` ([operación 10](../servicios/inventory.md#10-get-companiescompany_idbranchesbranch_idkardexcompany_product_id)); permiso `perm:inventory:movements:read`. Movimientos en orden cronológico con `previous_balance` y `new_balance`; `origin_type` y `origin_id` enlazan con la venta, compra, ajuste o conteo.
- Valoración FIFO: `GET …/branches/{branch_id}/valuation` y `…/valuation/{company_product_id}/layers` (operaciones 13 y 14); permiso `perm:inventory:valuation:read`.

## 5. Evolución de existencias de un período

`GET https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/branches/{branch_id}/stock-evolution?from=2026-10-01T00:00:00-05:00&to=2026-10-20T00:00:00-05:00` ([operación 37](../servicios/inventory.md#37-get-companiescompany_idbranchesbranch_idstock-evolution)); permiso `perm:inventory:stock_evolution:read`. Por producto: saldo inicial, entradas, salidas, reversos, ajustes y saldo final, sin costos. El mismo reporte, con nombres de producto y descarga CSV, está en [Business Reporting](../servicios/business-reporting.md#10-get-companiescompany_idbranchesbranch_idreportsstock-evolution).

## 6. Si hay que corregir existencias

Un ajuste manual es `HIGH_RISK` y exige asignación a la sucursal: `POST …/companies/{company_id}/inventory-adjustments` con `adjustment_key` (UUID de idempotencia), `adjustment_type`, `quantity` y `reason` ([Inventory, operación 16](../servicios/inventory.md#16-post-companiescompany_idinventory-adjustments)). Para un inventario físico completo use los conteos (operaciones 19–25): crear, iniciar, registrar cantidades contadas y completar.
