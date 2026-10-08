# Ejercicio 7: Anulación

Anular un borrador es local; anular una venta confirmada revierte exactamente su salida en Inventory y restituye las unidades con su costo.

Datos **ficticios** (ver `00-datos-ficticios.md`). El ejercicio es independiente: se ejecuta en una base nueva con el reloj fijo en el 5 de noviembre de 2026.

## Orden de los pasos

| Paso | Archivo | Llamada | Ejecuta | Estado |
| --- | --- | --- | --- | --- |
| 1 | [01-crear-la-secuencia.md](01-crear-la-secuencia.md) | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sale-sequences` | `ventas.test` | `201` |
| 2 | [02-borrador-a-anular.md](02-borrador-a-anular.md) | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales` | `ventas.test` | `201` |
| 3 | [03-anular-el-borrador.md](03-anular-el-borrador.md) | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<BORRADOR>/cancellation` | `ventas.test` | `200` |
| 4 | [04-venta-a-anular.md](04-venta-a-anular.md) | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales` | `ventas.test` | `201` |
| 5 | [05-confirmar.md](05-confirmar.md) | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/confirmation` | `ventas.test` | `200` |
| 6 | [06-anular-la-venta-confirmada.md](06-anular-la-venta-confirmada.md) | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/cancellation` | `ventas.test` | `200` |

## Por qué este orden

- La numeración necesita una secuencia activa antes de confirmar; la confirmación necesita un borrador; la anulación de una venta confirmada necesita su salida en Inventory.

## Variables

| Variable | Se guarda en | Se usa en |
| --- | --- | --- |
| `<SECUENCIA>` | paso 1 (`id`) | pasos — |
| `<BORRADOR>` | paso 2 (`id`) | pasos 3 |
| `<VENTA>` | paso 4 (`id`) | pasos 5, 6 |
