# Ejercicio 2: Venta en borrador y precios

El vendedor registra una venta en borrador: una línea en caja con la lista mayorista y otra con el precio de su presentación en la lista predeterminada. El precio siempre lo resuelve el sistema: se rechazan el precio manual, una lista inexistente, una lista sin precio para el producto y un producto sin control de inventario.

Datos **ficticios** (ver `00-datos-ficticios.md`). El ejercicio es independiente: se ejecuta en una base nueva con el reloj fijo en el 5 de noviembre de 2026.

## Orden de los pasos

| Paso | Archivo | Llamada | Ejecuta | Estado |
| --- | --- | --- | --- | --- |
| 1 | [01-crear-el-borrador.md](01-crear-el-borrador.md) | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales` | `ventas.test` | `201` |
| 2 | [02-agregar-una-linea.md](02-agregar-una-linea.md) | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/details` | `ventas.test` | `201` |
| 3 | [03-precio-manual.md](03-precio-manual.md) | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/details` | `ventas.test` | `422` |
| 4 | [03a-impuesto-adicional.md](03a-impuesto-adicional.md) | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/details` | `ventas.test` | `422` |
| 5 | [04-lista-inexistente.md](04-lista-inexistente.md) | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/details` | `ventas.test` | `422` |
| 6 | [05-lista-sin-precio.md](05-lista-sin-precio.md) | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/details` | `ventas.test` | `409` |
| 7 | [06-producto-sin-control-de-inventario.md](06-producto-sin-control-de-inventario.md) | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/details` | `ventas.test` | `409` |
| 8 | [07-version-vieja.md](07-version-vieja.md) | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/details` | `ventas.test` | `409` |
| 9 | [08-consultar-el-borrador.md](08-consultar-el-borrador.md) | `GET /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>` | `ventas.test` | `200` |

## Por qué este orden

- La numeración necesita una secuencia activa antes de confirmar; la confirmación necesita un borrador; la anulación de una venta confirmada necesita su salida en Inventory.

## Variables

| Variable | Se guarda en | Se usa en |
| --- | --- | --- |
| `<VENTA>` | paso 1 (`id`) | pasos 2, 3, 4, 5, 6, 7, 8, 9 |
