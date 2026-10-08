# Ejercicio 5: Existencias insuficientes

Vender más de lo que hay en la sucursal se rechaza completo: ni salida ni número.

Datos **ficticios** (ver `00-datos-ficticios.md`). El ejercicio es independiente: se ejecuta en una base nueva con el reloj fijo en el 5 de noviembre de 2026.

## Orden de los pasos

| Paso | Archivo | Llamada | Ejecuta | Estado |
| --- | --- | --- | --- | --- |
| 1 | [01-crear-la-secuencia.md](01-crear-la-secuencia.md) | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sale-sequences` | `ventas.test` | `201` |
| 2 | [02-crear-el-borrador.md](02-crear-el-borrador.md) | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales` | `ventas.test` | `201` |
| 3 | [03-confirmar.md](03-confirmar.md) | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/confirmation` | `ventas.test` | `409` |

## Por qué este orden

- La numeración necesita una secuencia activa antes de confirmar; la confirmación necesita un borrador; la anulación de una venta confirmada necesita su salida en Inventory.

## Variables

| Variable | Se guarda en | Se usa en |
| --- | --- | --- |
| `<SECUENCIA>` | paso 1 (`id`) | pasos — |
| `<VENTA>` | paso 2 (`id`) | pasos 3 |
