# Sales Service — Domain Map

## Responsabilidad
Registrar ventas a clientes, verificar precio y existencias, confirmar descontando el inventario de la
sucursal con su costo FIFO y su número oficial, y anular revirtiendo exactamente la salida
(`specs/015-sales-core/`).

## Entidades propietarias
- `Sale` (`sales`): cabecera; solo contado en el MVP; `inventory_operation_id`; `has_unknown_cost`.
- `SaleDetail` (`sale_details`): línea con precio resuelto y su origen, snapshots, costo FIFO (por
  unidad base) y margen.
- `SaleSequence` (`sale_sequences`) y `SaleSequenceCounter` (`sale_sequence_counters`): numeración con
  contador independiente por período.
- `SaleOperation` (`sale_operations`): confirmación o anulación distribuida, idempotente y reconciliable.

## Referencias externas principales
- empresa, sucursal (zona horaria) y usuario operativo → Operational Context Service
- cliente, producto, presentación, precio aplicable y listas de precios → Commercial Relationship Service
- presentación global, producto global y unidad base → Product Catalog Service
- identificación del cliente (persona u organización) → Party Identity Service
- saldos, salida con costo FIFO, reverso y consulta por clave → Inventory Service
- eventos de auditoría (outbox) → Audit Service

Sin FK físicas hacia otros servicios: solo UUID validados contra su dueño.

## Flujo base
`DRAFT` (precio resuelto, sin efectos en inventario) → consulta de disponibilidad (informativa) →
confirmación: verificación de precio (`409 PRICES_CHANGED`) y existencias → operación `PENDING` →
salida en Inventory (unidad base, sin costo) → `CONFIRMED` con costo FIFO, margen y número; o `PENDING`
recuperable por reintento o conciliador → anulación con reverso exacto (`CANCELLED`).

## Ubicación
`services/sales-service/docs/domain-map.md`
