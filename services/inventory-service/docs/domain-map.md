# Inventory Service — Domain Map

## Responsabilidad
Controlar saldos, movimientos, ajustes, políticas, conteos y valoración del inventario. La Fase A
(`specs/012-inventory-core/`) entrega el motor central: saldos, kardex, entradas de compra, salidas
de venta y sus reversos.

## Entidades propietarias
### Fase A — motor central (implementada)
- `InventoryBalance` (`inventory_balances`): saldo por empresa, sucursal y producto; nunca negativo.
- `InventoryMovement` (`inventory_movements`): kardex inmutable con `balance_sequence` sin huecos.
- `inventory_operations` (tabla de infraestructura): idempotencia (`operation_key`, `request_hash`) y
  agrupación de los movimientos de una operación o reverso.
- `audit_outbox` (de `libs/sio-audit`): eventos de auditoría pendientes de entregar.

### Fase B — gestión complementaria (bloque 13, pendiente)
- `InventoryAdjustment`
- `InventoryPolicy`
- `InventoryCount`
- `InventoryCountDetail`
- `CompanyInventoryPolicy`
- `InventoryCostLayer`, `InventoryCostConsumption` (valoración, si aplica)

## Referencias externas principales
- `company_id`, `branch_id`, `application_user_id` → Operational Context Service (validados al aplicar)
- `company_product_id` → Commercial Relationship Service (validado al aplicar)
- `origin_id`, `origin_detail_id` → documento de Purchase Service (entradas) o Sales Service (salidas),
  sin validar

## Consumidores
- Purchase Service: entradas y sus reversos (`perm:inventory:entries:create`).
- Sales Service: salidas, sus reversos y consulta de stock (`perm:inventory:outputs:create`,
  `perm:inventory:balances:read` + `perm:inventory:platform:lookup`).
- Usuarios (futuro frontend): stock y kardex de sus empresas.

## Emisión a Audit
Un evento por operación aplicada o revertida (`InventoryOperation`), por Transactional Outbox y
`inventory-audit-outbox-worker`.

## Ubicación
`services/inventory-service/docs/domain-map.md`
