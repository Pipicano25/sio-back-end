# Inventory Service — Domain Map

## Responsabilidad
Controlar saldos, movimientos, ajustes, políticas, conteos y valoración del inventario. La Fase A
(`specs/012-inventory-core/`) entrega el motor central: saldos, kardex, entradas de compra, salidas
de venta y sus reversos. La Fase B (`specs/013-inventory-complementary/`) agrega ajustes, conteos
físicos, políticas y la valoración FIFO dentro del mismo motor.

## Entidades propietarias
### Fase A — motor central (implementada)
- `InventoryBalance` (`inventory_balances`): saldo por empresa, sucursal y producto; nunca negativo;
  con su valor FIFO (`inventory_value`, `average_unit_cost`, `has_unknown_cost`).
- `InventoryMovement` (`inventory_movements`): kardex inmutable con `balance_sequence` sin huecos y,
  desde la Fase B, `unit_cost`, `movement_value` y `cost_known`.
- `inventory_operations` (tabla de infraestructura): idempotencia (`operation_key`, `request_hash`) y
  agrupación de los movimientos de una operación, reverso, ajuste o finalización de conteo.
- `audit_outbox` (de `libs/sio-audit`): eventos de auditoría pendientes de entregar.

### Fase B — gestión complementaria (implementada)
- `InventoryAdjustment` (`inventory_adjustments`): ajuste aplicado por un usuario asignado a la
  sucursal; inmutable.
- `InventoryCount` / `InventoryCountDetail` (`inventory_counts`, `inventory_count_details`): conteo
  físico y sus productos contados; al completarse, sus diferencias se aplican como ajustes.
- `CompanyInventoryPolicy` (`company_inventory_policies`): política de la empresa (solo `FIFO`).
- `InventoryPolicy` (`inventory_policies`): niveles de reposición por producto y sucursal.
- `InventoryCostLayer` / `InventoryCostConsumption` (`inventory_cost_layers`,
  `inventory_cost_consumptions`): capas FIFO (entrada, ajuste o apertura) y los consumos que explican
  el costo de cada movimiento.

## Referencias externas principales
- `company_id`, `branch_id`, `application_user_id` → Operational Context Service (validados al aplicar;
  el usuario operativo de ajustes y conteos sale de `operational-access`)
- `company_product_id` → Commercial Relationship Service (validado al aplicar)
- `currency_code` de las capas → `default_currency` de la empresa en Operational Context (copiada al
  crear cada capa; nula solo en las aperturas de la migración)
- `origin_id`, `origin_detail_id` → documento de Purchase Service (entradas) o Sales Service (salidas),
  sin validar

## Consumidores
- Purchase Service: entradas (con costo unitario en unidad base) y sus reversos
  (`perm:inventory:entries:create`).
- Sales Service: salidas, sus reversos y consulta de stock (`perm:inventory:outputs:create`,
  `perm:inventory:balances:read` + `perm:inventory:platform:lookup`); guarda el costo que informa la
  salida (`unit_cost`, `movement_value`) junto con `cost_known`.
- Usuarios (futuro frontend): stock, kardex, ajustes, conteos, políticas y valoración de sus empresas.

## Emisión a Audit
Un evento por operación aplicada o revertida (`InventoryOperation`), por ajuste
(`InventoryAdjustment`), por inicio, cancelación y finalización de conteo (`InventoryCount`, la
finalización como resumen) y por cambio de política (`CompanyInventoryPolicy`, `InventoryPolicy`),
por Transactional Outbox e `inventory-audit-outbox-worker`.

## Ubicación
`services/inventory-service/docs/domain-map.md`
