# Purchase Service — Domain Map

## Responsabilidad
Registrar y controlar el ciclo de vida de las compras y su impacto en inventario
(`specs/014-purchase-core/`).

## Entidades propietarias
- `Purchase` (`purchases`)
- `PurchaseDetail` (`purchase_details`)
- `PurchaseSequence` (`purchase_sequences`)
- `PurchaseSequenceCounter` (`purchase_sequence_counters`, contador por período; BR-14)
- `PurchaseOperation` (`purchase_operations`)
- `PurchaseLifecycleEvent` (`purchase_lifecycle_events`)

## Referencias externas principales (`UUID REF`, sin FK física)
- empresa, sucursal, usuario operativo → Operational Context Service
- proveedor, condición de pago, producto y presentación empresarial, producto de proveedor →
  Commercial Relationship Service
- presentación global, producto global y unidad (snapshots) → Product Catalog Service
- identificación del proveedor (snapshot) → Party Identity Service
- tipo de condición de pago (snapshot) → Payment Reference Service
- operación de entrada o reverso aplicada (`inventory_operation_id`) → Inventory Service

## Flujo base
`DRAFT → CONFIRMED` (operación `CONFIRM`: `PENDING → SUCCEEDED | FAILED`; entrada en Inventory y número
del período en la misma transacción local que confirma).
`DRAFT → CANCELLED` (local) y `CONFIRMED → CANCELLED` (operación `CANCEL`: reverso exacto en Inventory).
Operaciones `PENDING` → completadas por el reintento con la misma clave o por el conciliador.

## Ubicación
`services/purchase-service/docs/domain-map.md`
