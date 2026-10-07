# Ejercicio 3: Confirmación idempotente

La confirmación ingresa la mercancía en Inventory y asigna el número del período. Inventory no responde en el primer intento: la operación queda pendiente y el reintento con la misma clave la completa sin duplicar la entrada; repetirla de nuevo devuelve el mismo resultado.

Datos **ficticios** (ver `00-datos-ficticios.md`). El ejercicio es independiente: se ejecuta en una base nueva con el reloj fijo en el 5 de noviembre de 2026.

## Orden de los pasos

| Paso | Archivo | Llamada | Ejecuta | Estado |
| --- | --- | --- | --- | --- |
| 1 | [01-crear-la-secuencia.md](01-crear-la-secuencia.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchase-sequences` | `compras.test` | `201` |
| 2 | [02-crear-el-borrador.md](02-crear-el-borrador.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases` | `compras.test` | `201` |
| 3 | [03-confirmar-con-inventory-caido.md](03-confirmar-con-inventory-caido.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/confirmation` | `compras.test` | `503` |
| 4 | [04-reintentar-con-la-misma-clave.md](04-reintentar-con-la-misma-clave.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/confirmation` | `compras.test` | `200` |
| 5 | [05-repetir-la-confirmacion.md](05-repetir-la-confirmacion.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/confirmation` | `compras.test` | `200` |
| 6 | [06-consultar-las-operaciones.md](06-consultar-las-operaciones.md) | `GET /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/operations` | `compras.test` | `200` |

## Por qué este orden

- La numeración necesita una secuencia activa antes de confirmar; la confirmación necesita un borrador; la anulación y los hitos de recepción necesitan una compra confirmada.

## Variables

| Variable | Se guarda en | Se usa en |
| --- | --- | --- |
| `<SECUENCIA>` | paso 1 (`id`) | pasos — |
| `<COMPRA>` | paso 2 (`id`) | pasos 3, 4, 5, 6 |
| `<ENTRADA>` | paso 4 (`inventory_operation_id`) | pasos — |
