# 6.8 Inventario

[← API principales](README.md) · [← Índice](../index.md)

Consultar las existencias de la empresa y de cada sucursal, encontrar productos con disponibilidad, seguir los movimientos (kardex), ver cómo evolucionan las existencias y ejecutar las operaciones manuales implementadas: ajustes, conteos físicos y mínimos por producto.

Servicios implicados: [Product Inventory Query](../servicios/product-inventory-query.md) (vista consolidada de producto + precio + existencias, pensada para el frontend) e [Inventory](../servicios/inventory.md) (propietario de saldos, movimientos, costos, ajustes, conteos y políticas). Las existencias **entran** por la recepción de compras y **salen** por la confirmación de ventas; esas operaciones las invocan Purchase y Sales con cuenta técnica (Inventory 3–6) y **no** se llaman desde el frontend. Flujo con JSON: [Consultar inventario](../ejemplos/consultar-inventario.md).

| # | Funcionalidad | Método y ruta | Permiso | Ficha |
|---|---|---|---|---|
| 1 | Buscar productos con precio y existencias | `GET /api/v1/companies/{company_id}/product-overviews` · `…/branches/{branch_id}/product-overviews` (PIQS) | `perm:product-inventory-query:product_overviews:read` | [PIQS 3](../servicios/product-inventory-query.md#3-get-companiescompany_idproduct-overviews) · [PIQS 4](../servicios/product-inventory-query.md#4-get-companiescompany_idbranchesbranch_idproduct-overviews) |
| 2 | Existencias por producto, sucursal y empresa | `GET /api/v1/companies/{company_id}/inventory-overviews` · `…/branches/{branch_id}/inventory-overviews` (PIQS) | `perm:product-inventory-query:inventory_overviews:read` | [PIQS 5](../servicios/product-inventory-query.md#5-get-companiescompany_idinventory-overviews) · [PIQS 6](../servicios/product-inventory-query.md#6-get-companiescompany_idbranchesbranch_idinventory-overviews) |
| 3 | Productos bajo el mínimo | `GET /api/v1/companies/{company_id}/low-stock-products` · `…/branches/{branch_id}/low-stock-products` (PIQS) | `perm:product-inventory-query:low_stock_products:read` | [PIQS 7](../servicios/product-inventory-query.md#7-get-companiescompany_idlow-stock-products) · [PIQS 8](../servicios/product-inventory-query.md#8-get-companiescompany_idbranchesbranch_idlow-stock-products) |
| 4 | Indicadores de inventario | `GET /api/v1/companies/{company_id}/inventory-summary` · `…/branches/{branch_id}/inventory-summary` (PIQS) | `perm:product-inventory-query:inventory_summary:read` | [PIQS 9](../servicios/product-inventory-query.md#9-get-companiescompany_idinventory-summary) · [PIQS 10](../servicios/product-inventory-query.md#10-get-companiescompany_idbranchesbranch_idinventory-summary) |
| 5 | Saldo exacto de una sucursal | `GET /api/v1/companies/{company_id}/branches/{branch_id}/balances` · `…/balances/{company_product_id}` (Inventory) | `perm:inventory:balances:read` | [Inv 7](../servicios/inventory.md#7-get-companiescompany_idbranchesbranch_idbalances) · [Inv 8](../servicios/inventory.md#8-get-companiescompany_idbranchesbranch_idbalancescompany_product_id) |
| 6 | Kardex de un producto | `GET /api/v1/companies/{company_id}/branches/{branch_id}/kardex/{company_product_id}` (Inventory) | `perm:inventory:movements:read` | [Inv 10](../servicios/inventory.md#10-get-companiescompany_idbranchesbranch_idkardexcompany_product_id) |
| 7 | Valor del inventario de una sucursal | `GET /api/v1/companies/{company_id}/branches/{branch_id}/valuation` (Inventory) | `perm:inventory:valuation:read` | [Inv 13](../servicios/inventory.md#13-get-companiescompany_idbranchesbranch_idvaluation) |
| 8 | Registrar un ajuste manual | `POST /api/v1/companies/{company_id}/inventory-adjustments` (Inventory) | `perm:inventory:adjustments:create` + asignación a la sucursal | [Inv 16](../servicios/inventory.md#16-post-companiescompany_idinventory-adjustments) |
| 9 | Consultar ajustes | `GET /api/v1/companies/{company_id}/inventory-adjustments` (Inventory) | `perm:inventory:adjustments:read` | [Inv 17](../servicios/inventory.md#17-get-companiescompany_idinventory-adjustments) |
| 10 | Crear e iniciar un conteo físico | `POST /api/v1/companies/{company_id}/inventory-counts` · `…/{count_id}/start` (Inventory) | `perm:inventory:counts:create` + asignación | [Inv 19](../servicios/inventory.md#19-post-companiescompany_idinventory-counts) · [Inv 21](../servicios/inventory.md#21-post-companiescompany_idinventory-countscount_idstart) |
| 11 | Registrar cantidades contadas | `PUT /api/v1/companies/{company_id}/inventory-counts/{count_id}/details/{company_product_id}` (Inventory) | `perm:inventory:counts:create` + asignación | [Inv 22](../servicios/inventory.md#22-put-companiescompany_idinventory-countscount_iddetailscompany_product_id) |
| 12 | Completar o cancelar el conteo | `POST …/inventory-counts/{count_id}/complete` · `…/cancel` (Inventory) | `perm:inventory:counts:create` + asignación | [Inv 23](../servicios/inventory.md#23-post-companiescompany_idinventory-countscount_idcomplete) · [Inv 24](../servicios/inventory.md#24-post-companiescompany_idinventory-countscount_idcancel) |
| 13 | Consultar conteos | `GET /api/v1/companies/{company_id}/inventory-counts` · `…/{count_id}` (Inventory) | `perm:inventory:counts:read` | [Inv 20](../servicios/inventory.md#20-get-companiescompany_idinventory-counts) · [Inv 25](../servicios/inventory.md#25-get-companiescompany_idinventory-countscount_id) |
| 14 | Definir el mínimo de un producto en una sucursal | `POST /api/v1/companies/{company_id}/inventory-policies` · `GET` (Inventory) | `perm:inventory:product-policies:update` · `…:read` | [Inv 30](../servicios/inventory.md#30-post-companiescompany_idinventory-policies) · [Inv 29](../servicios/inventory.md#29-get-companiescompany_idinventory-policies) |

Bases: Product Inventory Query `https://sio-product-inventory-query-dev.onrender.com/api/v1`; Inventory `https://sio-inventory-dev.onrender.com/api/v1`.

No se consideran principales (ver la ficha de Inventory): aplicar y revertir entradas y salidas (3–6, solo cuentas técnicas), saldos por lotes (9), operaciones por id o clave (11, 12), capas FIFO y consumos de costo (14, 15), ajuste por id (18), política general de la empresa (26–28), modificar o inactivar políticas de producto (31–34), conjuntos de productos (35), indicadores detallados (36) y la evolución de existencias (37, 38), que se consulta desde [Reportes](reportes.md).

---

## Reglas verificadas

- **Unidad base.** Inventory lleva las existencias en la unidad base del producto (`company_product_id`), no por presentación. Una venta de 2 cajas × 100 descuenta 200 unidades base (`base_quantity`).
- **Alcance.** Las lecturas de Inventory y de Product Inventory Query exigen membresía `ACTIVE` en la empresa; los ajustes y conteos exigen además asignación `ACTIVE` a la sucursal (`403 INVENTORY.BRANCH_ACCESS_DENIED`). Una sucursal de otra empresa responde `404`.
- **Control de inventario por producto.** Solo los productos con `inventory_control_enabled: true` (configurado al adoptarlos) tienen saldos; para los demás, Product Inventory Query devuelve `stock: null`.
- **Costeo FIFO.** Cada entrada abre una capa de costo; las salidas consumen las capas más antiguas. `average_unit_cost` e `inventory_value` salen de las capas abiertas; `has_unknown_cost: true` indica movimientos sin costo conocido.
- **Idempotencia.** Los ajustes llevan `adjustment_key` y la finalización de conteos `completion_key` (UUID generados por el frontend): repetir la llamada con la misma clave no duplica el movimiento.

## 1. Buscar productos con precio y existencias

**¿Qué puede hacer el usuario?** Ver el catálogo de la empresa con imagen, códigos, presentaciones, precio y existencias, en una sola consulta; es la pantalla de productos de ventas, compras e inventario.

**¿Qué API debe consumir el frontend?** `GET https://sio-product-inventory-query-dev.onrender.com/api/v1/companies/{company_id}/product-overviews` (existencias de todas las sucursales activas, o de `branch_id[]`) o `…/companies/{company_id}/branches/{branch_id}/product-overviews` (una sucursal). Permiso `perm:product-inventory-query:product_overviews:read`; los filtros de existencias exigen además `perm:product-inventory-query:stock:read` y los de mínimos `perm:inventory:product-policies:read`. Consulta: `search` (≤ 200), `internal_code`, `sku`, `barcode`, `identifier`, `brand_id[]`, `category_id[]` + `include_descendants`, `status` (`ACTIVE` por defecto), `product_type`, `has_image`, `stock_state` (`IN_STOCK`, `OUT_OF_STOCK`), `price_list_id`, `sort` (`display_name`, `internal_code`, `created_at` con `:asc`/`:desc`), `page_size` (1–20), `cursor`.

**¿Qué necesita antes?** [company_id](../parametros/company-id.md) y, para la variante por sucursal, [branch_id](../parametros/branch-id.md). Opcionalmente el [price_list_id](../parametros/price-list-id.md) cuyo precio se quiere mostrar.

**¿Cómo sabe que funcionó?** `200` con `items[]` (producto, `brand`, `categories[]`, `identifiers[]`, `base_unit`, `has_image`, `image_url`, `presentations[]` con `price`, y `stock`), `has_next`, `next_cursor`, `partial` y `partial_reason` (alguna fuente no respondió: los datos ausentes vienen `null`), `sort_applied`, `resolved_at`. La paginación es por cursor: envía `cursor=next_cursor` para la página siguiente; `pagination_reset: true` indica que el cursor dejó de ser válido y se reinició.

## 2. Existencias por producto, sucursal y empresa

**¿Qué puede hacer el usuario?** Ver cuánto hay de cada producto en cada sucursal y el total de la empresa, sin precios.

**¿Qué API debe consumir el frontend?** `GET https://sio-product-inventory-query-dev.onrender.com/api/v1/companies/{company_id}/inventory-overviews` (`branch_id[]` o `scope=COMPANY`) o `…/branches/{branch_id}/inventory-overviews`. Permiso `perm:product-inventory-query:inventory_overviews:read`. Mismos filtros de producto que la funcionalidad 1, más `stock_state` y `minimum_state` (`NO_POLICY`, `BELOW_MINIMUM`, `AT_MINIMUM`, `ABOVE_MINIMUM`).

**¿Cómo sabe que funcionó?** `200` con `items[]` por producto, con las existencias por sucursal y el consolidado, paginado por cursor como la funcionalidad 1.

## 3. Productos bajo el mínimo

`GET https://sio-product-inventory-query-dev.onrender.com/api/v1/companies/{company_id}/low-stock-products` (o por sucursal). Permiso `perm:product-inventory-query:low_stock_products:read` (más lectura de existencias y de políticas). Responde `200` con `items[]` de pares producto–sucursal: `company_product_id`, `display_name`, `branch_id`, `base_quantity` (existencia), `minimum_stock`, `shortfall` (faltante), `policy_status`. Solo aparecen productos con política de mínimo activa (funcionalidad 14).

## 4. Indicadores de inventario

`GET https://sio-product-inventory-query-dev.onrender.com/api/v1/companies/{company_id}/inventory-summary` (o por sucursal; `branch_id[]` o `scope=COMPANY`). Permiso `perm:product-inventory-query:inventory_summary:read`. Responde `200` con `adopted_products`, `branches[]` y `consolidated` (`products_with_positive_balance`, `products_with_zero_balance`, `products_with_policy`, `products_below_minimum`) y `resolved_at`. Es el tablero de inicio del módulo.

## 5. Saldo exacto de una sucursal

`GET https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/branches/{branch_id}/balances?in_stock_only=true` (permiso `perm:inventory:balances:read`; también `company_product_id`, `page`, `page_size`) o `…/balances/{company_product_id}` para un producto. Responde `200` con `quantity` (unidad base), `last_movement_at`, `balance_sequence`, `inventory_value`, `average_unit_cost`, `has_unknown_cost`. Es la fuente que usan Sales (disponibilidad) y Product Inventory Query; consúltala directamente cuando necesites el saldo sin el resto del producto.

## 6. Kardex de un producto

**¿Qué puede hacer el usuario?** Ver la historia de movimientos de un producto en una sucursal: compras recibidas, ventas, ajustes, reversos, con saldo antes y después.

**¿Qué API debe consumir el frontend?** `GET https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/branches/{branch_id}/kardex/{company_product_id}`. Permiso `perm:inventory:movements:read`. Consulta: `occurred_at_from`, `occurred_at_to`, `movement_type` (`PURCHASE_ENTRY`, `SALE_OUTPUT`, `POSITIVE_ADJUSTMENT`, `NEGATIVE_ADJUSTMENT`, `ENTRY_REVERSAL`, `OUTPUT_REVERSAL`), `origin_type` (`PURCHASE`, `SALE`, `ADJUSTMENT`, `COUNT`), `origin_id` (el [purchase_id](../parametros/purchase-id.md) o [sale_id](../parametros/sale-id.md)), `page`, `page_size`.

**¿Cómo sabe que funcionó?** `200` con `items[]` en orden cronológico: `movement_type`, `quantity`, `previous_balance`, `new_balance`, `unit_cost`, `cost_known`, `origin_type`, `origin_id`, `application_user_id`, `reason`, `created_at`. Para saltar al documento de origen usa `origin_type` + `origin_id`.

## 7. Valor del inventario de una sucursal

`GET https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/branches/{branch_id}/valuation` (permiso `perm:inventory:valuation:read`). Responde `200` con `items[]` (`company_product_id`, `quantity`, `inventory_value`, `average_unit_cost`, `open_layers`, `has_unknown_cost`) y `total_value`. Capas de un producto: `…/valuation/{company_product_id}/layers` (Inv 14).

## 8. Registrar un ajuste manual

**¿Qué puede hacer el usuario?** Corregir el saldo de un producto por merma, rotura, hallazgo o error, dejando el motivo.

**¿Qué API debe consumir el frontend?** `POST https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/inventory-adjustments`. Permiso `perm:inventory:adjustments:create` + asignación a la sucursal (`HIGH_RISK`). Cuerpo `AdjustmentIn`:

```json
{
  "adjustment_key": "7275dce1-3641-4e91-8854-2271a233576f",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
  "adjustment_type": "POSITIVE",
  "quantity": "2",
  "unit_cost": "500.00",
  "reason": "Hallazgo en inventario físico"
}
```

`adjustment_key` es un UUID nuevo por ajuste (idempotencia); `unit_cost` solo aplica a los positivos (abre una capa de costo); `quantity` va en unidad base.

**¿Cómo sabe que funcionó?** `201` con el ajuste aplicado: `id`, `operation_id`, `movement_id`, `previous_balance`, `new_balance`, `adjustment_value` y el `movement` creado. Errores: `403 BRANCH_ACCESS_DENIED`, `409` si un ajuste negativo deja el saldo por debajo de cero (ver `errors[]`), `409` si la misma `adjustment_key` ya se usó con otro cuerpo, `422 VALIDATION_ERROR`.

## 9. Consultar ajustes

`GET https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/inventory-adjustments` (permiso `perm:inventory:adjustments:read`; filtros `branch_id`, `company_product_id`, `adjustment_type`, `inventory_count_id`, `created_at_from`, `created_at_to`, `page`, `page_size`; más recientes primero). Responde `200` con `PaginatedResponse` de ajustes, cada uno con su `inventory_count_id` cuando provino de un conteo.

## 10 a 13. Conteo físico

**¿Qué puede hacer el usuario?** Hacer un inventario físico de la sucursal: abrir el conteo, registrar lo contado producto por producto y, al completar, dejar que el sistema aplique las diferencias como ajustes de una sola vez.

**¿Qué API debe consumir el frontend?** (base `https://sio-inventory-dev.onrender.com/api/v1`, permiso `perm:inventory:counts:create` + asignación para las escrituras y `perm:inventory:counts:read` para las lecturas):

| Paso | Método y ruta | Cuerpo | Resultado |
|---|---|---|---|
| Crear | `POST /companies/{company_id}/inventory-counts` | `{"branch_id": "…", "observations": "…"}` | `201`, `status: "DRAFT"`, `id` = `count_id`, `version` |
| Iniciar | `POST /companies/{company_id}/inventory-counts/{count_id}/start` | `{"version": n}` | `200`, `status: "IN_PROGRESS"`; solo un conteo en curso por sucursal |
| Contar | `PUT /companies/{company_id}/inventory-counts/{count_id}/details/{company_product_id}` | `{"counted_quantity": "40", "unit_cost": "500.00"}` | `200` con `system_quantity_snapshot`, `counted_quantity`, `difference_quantity`; repetir reemplaza la cantidad |
| Completar | `POST /companies/{company_id}/inventory-counts/{count_id}/complete` | `{"completion_key": "<uuid>", "version": n}` | `200`, `status: "COMPLETED"`, `operation_id`; aplica todas las diferencias como ajustes, todo o nada |
| Cancelar | `POST /companies/{company_id}/inventory-counts/{count_id}/cancel` | `{"version": n, "reason": "…"}` | `200`, `status: "CANCELLED"`, sin efectos en saldos |
| Consultar | `GET /companies/{company_id}/inventory-counts?branch_id=…&status=…` · `GET …/inventory-counts/{count_id}` | — | `200`; el detalle trae `details[]` y los ajustes generados |

**¿Qué necesita antes?** Sucursal asignada al usuario y, para contar, los [company_product_id](../parametros/company-product-id.md) (la funcionalidad 1 o 5 da la lista de la sucursal).

**¿Cómo sabe que funcionó?** Tras completar, el kardex de cada producto con diferencia muestra un `POSITIVE_ADJUSTMENT` o `NEGATIVE_ADJUSTMENT` con `origin_type: "COUNT"` y `origin_id` = `count_id`. Errores: `409 VERSION_CONFLICT`, `409 INVALID_COUNT_TRANSITION` (`DRAFT → IN_PROGRESS → COMPLETED | CANCELLED`), `409 COUNT_ALREADY_IN_PROGRESS` (ya hay un conteo en curso en la sucursal), `403 BRANCH_ACCESS_DENIED`.

## 14. Definir el mínimo de un producto en una sucursal

`POST https://sio-inventory-dev.onrender.com/api/v1/companies/{company_id}/inventory-policies` (permiso `perm:inventory:product-policies:update`) con `branch_id`, `company_product_id`, `minimum_stock`, `safety_stock_method` (`BASIC`, `STATISTICAL`), `replenishment_mode` (`MANUAL`, `AUTO_DRAFT`), `target_stock`, `service_level`, `calculation_window_days`, `auto_purchase_enabled`. Una sola política activa por producto y sucursal. Responde `201` con `is_active: true`. Consulta: `GET …/inventory-policies?branch_id=…&company_product_id=…` (Inv 29). Con la política creada, el producto aparece en la funcionalidad 3 cuando su existencia baja de `minimum_stock`. `replenishment_mode: AUTO_DRAFT` y `auto_purchase_enabled` son **solo configuración** (verificado en el código de Inventory): se guardan en la política sin cambiar el motor de inventario ni generar compras; ninguna de las 411 operaciones crea compras automáticamente.

## Dependencias con otros módulos

- [Compras](compras.md): la recepción crea las entradas (`PURCHASE_ENTRY`) y las capas de costo.
- [Ventas](ventas.md): la confirmación crea las salidas (`SALE_OUTPUT`); la disponibilidad se calcula sobre estos saldos.
- [Productos y precios](productos-y-precios.md): `inventory_control_enabled` al adoptar el producto decide si tiene saldos; el precio mostrado por Product Inventory Query sale de las listas.
- [Administración empresarial](administracion-empresarial.md): asignación de sucursales para ajustes y conteos.
- [Reportes](reportes.md): evolución de existencias por período.
