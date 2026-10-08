# Ejercicio 8: Consultas

Listado filtrado de ventas de la empresa y aislamiento: otra empresa responde `404` sin revelar existencia.

Datos **ficticios** (ver `00-datos-ficticios.md`). El ejercicio es independiente: se ejecuta en una base nueva con el reloj fijo en el 5 de noviembre de 2026.

## Orden de los pasos

| Paso | Archivo | Llamada | Ejecuta | Estado |
| --- | --- | --- | --- | --- |
| 1 | [01-crear-la-secuencia.md](01-crear-la-secuencia.md) | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sale-sequences` | `ventas.test` | `201` |
| 2 | [02-venta.md](02-venta.md) | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales` | `ventas.test` | `201` |
| 3 | [03-confirmar.md](03-confirmar.md) | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/confirmation` | `ventas.test` | `200` |
| 4 | [04-listar-confirmadas.md](04-listar-confirmadas.md) | `GET /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales?status=CONFIRMED&number=FV-202611-000001` | `reportes.test` | `200` |
| 5 | [05-otra-empresa.md](05-otra-empresa.md) | `GET /api/v1/companies/d15a0000-0000-4000-8000-000000000099/sales/<VENTA>` | `reportes.test` | `404` |

## Por qué este orden

- La numeración necesita una secuencia activa antes de confirmar; la confirmación necesita un borrador; la anulación de una venta confirmada necesita su salida en Inventory.

## Variables

| Variable | Se guarda en | Se usa en |
| --- | --- | --- |
| `<SECUENCIA>` | paso 1 (`id`) | pasos — |
| `<VENTA>` | paso 2 (`id`) | pasos 3, 5 |
