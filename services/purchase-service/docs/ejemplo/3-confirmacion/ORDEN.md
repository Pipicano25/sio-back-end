# Ejercicio 3: Confirmación y recepción idempotente

Spec 020: confirmar asigna el número del período y deja la compra pendiente de recepción, **sin** mover inventario. La recepción física completa ingresa la mercancía en Inventory: Inventory no responde en el primer intento, la operación queda pendiente y el reintento con la misma clave la completa sin duplicar la entrada; repetirla de nuevo devuelve el mismo resultado.

Datos **ficticios** (ver `00-datos-ficticios.md`). El ejercicio es independiente: se ejecuta en una base nueva con el reloj fijo en el 5 de noviembre de 2026.

## Orden de los pasos

| Paso | Archivo | Llamada | Ejecuta | Estado |
| --- | --- | --- | --- | --- |
| 1 | [01-crear-la-secuencia.md](01-crear-la-secuencia.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchase-sequences` | `compras.test` | `201` |
| 2 | [02-crear-el-borrador.md](02-crear-el-borrador.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases` | `compras.test` | `201` |
| 3 | [03-confirmar.md](03-confirmar.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/confirmation` | `compras.test` | `200` |
| 4 | [04-recibir-con-inventory-caido.md](04-recibir-con-inventory-caido.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/receipt` | `compras.test` | `503` |
| 5 | [05-reintentar-con-la-misma-clave.md](05-reintentar-con-la-misma-clave.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/receipt` | `compras.test` | `200` |
| 6 | [06-repetir-la-recepcion.md](06-repetir-la-recepcion.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/receipt` | `compras.test` | `200` |
| 7 | [07-consultar-las-operaciones.md](07-consultar-las-operaciones.md) | `GET /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/operations` | `compras.test` | `200` |

## Por qué este orden

- La numeración necesita una secuencia activa antes de confirmar; la confirmación necesita un borrador; la anulación y los hitos de recepción necesitan una compra confirmada.

## Variables

| Variable | Se guarda en | Se usa en |
| --- | --- | --- |
| `<SECUENCIA>` | paso 1 (`id`) | pasos — |
| `<COMPRA>` | paso 2 (`id`) | pasos 3, 4, 5, 6, 7 |
| `<VERSION_CONFIRMADA>` | paso 3 (`version`) | pasos 4, 5, 6 |
| `<ENTRADA>` | paso 5 (`inventory_operation_id`) | pasos — |
