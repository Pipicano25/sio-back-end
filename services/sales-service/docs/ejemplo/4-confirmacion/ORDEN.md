# Ejercicio 4: Confirmación: precio cambiado e idempotencia

La confirmación vuelve a verificar el precio: si cambió, se rechaza sin efectos y el vendedor actualiza la línea. Luego Inventory no responde: la operación queda pendiente y el reintento con la misma clave la completa sin duplicar la salida; repetirla de nuevo devuelve el mismo resultado.

Datos **ficticios** (ver `00-datos-ficticios.md`). El ejercicio es independiente: se ejecuta en una base nueva con el reloj fijo en el 5 de noviembre de 2026.

## Orden de los pasos

| Paso | Archivo | Llamada | Ejecuta | Estado |
| --- | --- | --- | --- | --- |
| 1 | [01-crear-la-secuencia.md](01-crear-la-secuencia.md) | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sale-sequences` | `ventas.test` | `201` |
| 2 | [02-crear-el-borrador.md](02-crear-el-borrador.md) | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales` | `ventas.test` | `201` |
| 3 | [03-confirmar-con-precio-cambiado.md](03-confirmar-con-precio-cambiado.md) | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/confirmation` | `ventas.test` | `409` |
| 4 | [04-actualizar-la-linea.md](04-actualizar-la-linea.md) | `PUT /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/details/<LINEA>` | `ventas.test` | `200` |
| 5 | [05-confirmar-con-inventory-caido.md](05-confirmar-con-inventory-caido.md) | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/confirmation` | `ventas.test` | `503` |
| 6 | [06-reintentar-con-la-misma-clave.md](06-reintentar-con-la-misma-clave.md) | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/confirmation` | `ventas.test` | `200` |
| 7 | [07-repetir-la-confirmacion.md](07-repetir-la-confirmacion.md) | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/confirmation` | `ventas.test` | `200` |
| 8 | [08-consultar-las-operaciones.md](08-consultar-las-operaciones.md) | `GET /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/operations` | `ventas.test` | `200` |

## Por qué este orden

- La numeración necesita una secuencia activa antes de confirmar; la confirmación necesita un borrador; la anulación de una venta confirmada necesita su salida en Inventory.

## Variables

| Variable | Se guarda en | Se usa en |
| --- | --- | --- |
| `<SECUENCIA>` | paso 1 (`id`) | pasos — |
| `<VENTA>` | paso 2 (`id`) | pasos 3, 4, 5, 6, 7, 8 |
| `<LINEA>` | paso 2 (`lines[0].id`) | pasos 4 |
