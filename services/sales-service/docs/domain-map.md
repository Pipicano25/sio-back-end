# Sales Service — Domain Map

## Responsabilidad
Registrar ventas, validar disponibilidad y generar la salida correspondiente de inventario.

## Entidades propietarias
- `Sale`
- `SaleDetail`
- `SaleSequence`
- `SaleOperation`

## Referencias externas principales
- empresa/sucursal → Operational Context Service
- cliente, producto, presentación y origen del precio → Commercial Relationship Service
- confirmación de venta → valida y genera salida en Inventory Service

## Flujo base
`DRAFT → validación de stock → CONFIRMED → salida de inventario`.

## Ubicación
`services/sales-service/docs/domain-map.md`
