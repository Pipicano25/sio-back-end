# Ejercicio 1: Secuencias de numeración

El vendedor configura la numeración de ventas de la empresa: una secuencia mensual, su consulta con contadores por período y el rechazo de una segunda secuencia activa en el mismo alcance.

Datos **ficticios** (ver `00-datos-ficticios.md`). El ejercicio es independiente: se ejecuta en una base nueva con el reloj fijo en el 5 de noviembre de 2026.

## Orden de los pasos

| Paso | Archivo | Llamada | Ejecuta | Estado |
| --- | --- | --- | --- | --- |
| 1 | [01-crear-la-secuencia.md](01-crear-la-secuencia.md) | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sale-sequences` | `ventas.test` | `201` |
| 2 | [02-consultar-las-secuencias.md](02-consultar-las-secuencias.md) | `GET /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sale-sequences` | `ventas.test` | `200` |
| 3 | [03-segunda-secuencia-activa.md](03-segunda-secuencia-activa.md) | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sale-sequences` | `ventas.test` | `409` |

## Por qué este orden

- La numeración necesita una secuencia activa antes de confirmar; la confirmación necesita un borrador; la anulación de una venta confirmada necesita su salida en Inventory.

## Variables

| Variable | Se guarda en | Se usa en |
| --- | --- | --- |
| `<SECUENCIA>` | paso 1 (`id`) | pasos — |
