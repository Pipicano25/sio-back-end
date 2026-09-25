# Purchase Service — Domain Map

## Responsabilidad
Registrar y controlar el ciclo de vida de las compras y su impacto en inventario.

## Entidades propietarias
- `Purchase`
- `PurchaseDetail`
- `PurchaseSequence`
- `PurchaseOperation`
- `PurchaseLifecycleEvent`

## Referencias externas principales
- empresa/sucursal → Operational Context Service
- proveedor, producto y presentación empresarial → Commercial Relationship Service
- confirmación de compra → genera entrada en Inventory Service

## Flujo base
`DRAFT → CONFIRMED → entrada de inventario`  
`CONFIRMED → CANCELLED/REVERSED` según reglas del dominio.

## Ubicación
`services/purchase-service/docs/domain-map.md`
