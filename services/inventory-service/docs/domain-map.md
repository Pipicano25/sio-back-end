# Inventory Service — Domain Map

## Responsabilidad
Controlar saldos, movimientos, ajustes, políticas, conteos y valoración del inventario.

## Entidades propietarias
### MVP / núcleo
- `InventoryBalance`
- `InventoryMovement`
- `InventoryAdjustment`
- `InventoryPolicy`
- `InventoryCount`
- `InventoryCountDetail`

### Evolución / valoración
- `CompanyInventoryPolicy`
- `InventoryCostLayer`
- `InventoryCostConsumption`

## Referencias externas principales
- `company_id`, `branch_id` → Operational Context Service
- `company_product_id` → Commercial Relationship Service
- origen de compras → Purchase Service
- origen de ventas → Sales Service

## Ubicación
`services/inventory-service/docs/domain-map.md`
