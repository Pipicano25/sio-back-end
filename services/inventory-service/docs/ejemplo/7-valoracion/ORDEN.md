# Ejercicio 7: Valoración FIFO

Dos entradas con costos distintos, una salida que consume dos capas, el valor de la sucursal, las capas y los consumos de la salida, y los reversos con valoración: una entrada cuya capa ya se consumió no se revierte hasta revertir la venta.

Datos **ficticios** (ver `00-datos-ficticios.md`). El ejercicio es independiente: se ejecuta en una base nueva.

## Orden de los pasos

| Paso | Archivo | Llamada | Ejecuta | Estado |
| --- | --- | --- | --- | --- |
| 1 | [01-entrada-a-1000.md](01-entrada-a-1000.md) | `POST /api/v1/inventory-entries` | `inventory-test-operator` (cuenta de servicio) | `201` |
| 2 | [02-entrada-a-1300.md](02-entrada-a-1300.md) | `POST /api/v1/inventory-entries` | `inventory-test-operator` (cuenta de servicio) | `201` |
| 3 | [03-salida-de-12.md](03-salida-de-12.md) | `POST /api/v1/inventory-outputs` | `inventory-test-operator` (cuenta de servicio) | `201` |
| 4 | [04-valor-de-la-sucursal.md](04-valor-de-la-sucursal.md) | `GET /api/v1/companies/d44a0000-0000-4000-8000-000000000001/branches/d44b0000-0000-4000-8000-000000000001/valuation` | `inventario.test` | `200` |
| 5 | [05-capas.md](05-capas.md) | `GET /api/v1/companies/d44a0000-0000-4000-8000-000000000001/branches/d44b0000-0000-4000-8000-000000000001/valuation/d44d0000-0000-4000-8000-000000000001/layers?include_closed=true` | `inventario.test` | `200` |
| 6 | [06-consumos-de-la-salida.md](06-consumos-de-la-salida.md) | `GET /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-movements/<MOV_SALIDA>/cost-consumptions` | `inventario.test` | `200` |
| 7 | [07-reverso-de-entrada-consumida.md](07-reverso-de-entrada-consumida.md) | `POST /api/v1/inventory-entries/<OP_ENTRADA>/reversal` | `inventory-test-operator` (cuenta de servicio) | `409` |
| 8 | [08-reverso-de-la-salida.md](08-reverso-de-la-salida.md) | `POST /api/v1/inventory-outputs/<OP_SALIDA>/reversal` | `inventory-test-operator` (cuenta de servicio) | `201` |
| 9 | [09-reverso-de-entrada-intacta.md](09-reverso-de-entrada-intacta.md) | `POST /api/v1/inventory-entries/<OP_ENTRADA>/reversal` | `inventory-test-operator` (cuenta de servicio) | `201` |

## Por qué este orden

- Los saldos nacen de las entradas: las entradas van primero; las salidas, reversos y consultas dependen del saldo que dejan los pasos anteriores.

## Variables

| Variable | Se guarda en | Se usa en |
| --- | --- | --- |
| `<OP_ENTRADA>` | paso 1 (`id`) | pasos 7, 9 |
| `<OP_SALIDA>` | paso 3 (`id`) | pasos 8 |
| `<MOV_SALIDA>` | paso 3 (`movements[0].id`) | pasos 6 |
