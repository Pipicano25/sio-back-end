# Ejercicio 6: Rentabilidad y costo desconocido

Al confirmar, la venta guarda el costo FIFO que informa Inventory (por unidad base) y el margen. Solo quien tiene `perm:sales:sales:read-profitability` los ve. Con unidades de apertura sin costo histórico la venta se confirma igual, sin margen y con el indicador `has_unknown_cost`.

Datos **ficticios** (ver `00-datos-ficticios.md`). El ejercicio es independiente: se ejecuta en una base nueva con el reloj fijo en el 5 de noviembre de 2026.

## Orden de los pasos

| Paso | Archivo | Llamada | Ejecuta | Estado |
| --- | --- | --- | --- | --- |
| 1 | [01-crear-la-secuencia.md](01-crear-la-secuencia.md) | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sale-sequences` | `ventas.test` | `201` |
| 2 | [02-crear-la-venta.md](02-crear-la-venta.md) | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales` | `ventas.test` | `201` |
| 3 | [03-confirmar.md](03-confirmar.md) | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/confirmation` | `ventas.test` | `200` |
| 4 | [04-consultar-como-vendedor.md](04-consultar-como-vendedor.md) | `GET /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>` | `ventas.test` | `200` |
| 5 | [05-consultar-como-supervisor.md](05-consultar-como-supervisor.md) | `GET /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>` | `supervisor.test` | `200` |
| 6 | [06-venta-con-costo-desconocido.md](06-venta-con-costo-desconocido.md) | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales` | `ventas.test` | `201` |
| 7 | [07-confirmar.md](07-confirmar.md) | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<APERTURA>/confirmation` | `ventas.test` | `200` |
| 8 | [08-consultar-como-supervisor.md](08-consultar-como-supervisor.md) | `GET /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<APERTURA>` | `supervisor.test` | `200` |

## Por qué este orden

- La numeración necesita una secuencia activa antes de confirmar; la confirmación necesita un borrador; la anulación de una venta confirmada necesita su salida en Inventory.

## Variables

| Variable | Se guarda en | Se usa en |
| --- | --- | --- |
| `<SECUENCIA>` | paso 1 (`id`) | pasos — |
| `<VENTA>` | paso 2 (`id`) | pasos 3, 4, 5 |
| `<APERTURA>` | paso 6 (`id`) | pasos 7, 8 |
