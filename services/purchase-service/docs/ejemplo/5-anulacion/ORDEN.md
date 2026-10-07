# Ejercicio 5: Anulación

Anular un borrador es local; anular una compra confirmada revierte exactamente su entrada en Inventory; si esas unidades ya se consumieron, la anulación se rechaza y la compra sigue confirmada.

Datos **ficticios** (ver `00-datos-ficticios.md`). El ejercicio es independiente: se ejecuta en una base nueva con el reloj fijo en el 5 de noviembre de 2026.

## Orden de los pasos

| Paso | Archivo | Llamada | Ejecuta | Estado |
| --- | --- | --- | --- | --- |
| 1 | [01-crear-la-secuencia.md](01-crear-la-secuencia.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchase-sequences` | `compras.test` | `201` |
| 2 | [02-borrador-a-anular.md](02-borrador-a-anular.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases` | `compras.test` | `201` |
| 3 | [03-anular-el-borrador.md](03-anular-el-borrador.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<BORRADOR>/cancellation` | `compras.test` | `200` |
| 4 | [04-compra-a-anular.md](04-compra-a-anular.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases` | `compras.test` | `201` |
| 5 | [05-confirmar.md](05-confirmar.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/confirmation` | `compras.test` | `200` |
| 6 | [06-anular-la-compra-confirmada.md](06-anular-la-compra-confirmada.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/cancellation` | `compras.test` | `200` |
| 7 | [07-compra-vendida.md](07-compra-vendida.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases` | `compras.test` | `201` |
| 8 | [08-confirmar-la-otra.md](08-confirmar-la-otra.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<VENDIDA>/confirmation` | `compras.test` | `200` |
| 9 | [09-anular-con-inventario-consumido.md](09-anular-con-inventario-consumido.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<VENDIDA>/cancellation` | `compras.test` | `409` |

## Por qué este orden

- La numeración necesita una secuencia activa antes de confirmar; la confirmación necesita un borrador; la anulación y los hitos de recepción necesitan una compra confirmada.

## Variables

| Variable | Se guarda en | Se usa en |
| --- | --- | --- |
| `<SECUENCIA>` | paso 1 (`id`) | pasos — |
| `<BORRADOR>` | paso 2 (`id`) | pasos 3 |
| `<COMPRA>` | paso 4 (`id`) | pasos 5, 6 |
| `<ENTRADA>` | paso 5 (`inventory_operation_id`) | pasos — |
| `<VENDIDA>` | paso 7 (`id`) | pasos 8, 9 |
| `<ENTRADA_VENDIDA>` | paso 8 (`inventory_operation_id`) | pasos — |
