# Ejercicio 5: Anulación

Anular un borrador o una compra confirmada **pendiente de recepción** es local (spec 020: no hay entrada que revertir); anular una compra recibida revierte exactamente su entrada en Inventory; si esas unidades ya se consumieron, la anulación se rechaza y la compra sigue confirmada.

Datos **ficticios** (ver `00-datos-ficticios.md`). El ejercicio es independiente: se ejecuta en una base nueva con el reloj fijo en el 5 de noviembre de 2026.

## Orden de los pasos

| Paso | Archivo | Llamada | Ejecuta | Estado |
| --- | --- | --- | --- | --- |
| 1 | [01-crear-la-secuencia.md](01-crear-la-secuencia.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchase-sequences` | `compras.test` | `201` |
| 2 | [02-borrador-a-anular.md](02-borrador-a-anular.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases` | `compras.test` | `201` |
| 3 | [03-anular-el-borrador.md](03-anular-el-borrador.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<BORRADOR>/cancellation` | `compras.test` | `200` |
| 4 | [04-compra-sin-recibir.md](04-compra-sin-recibir.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases` | `compras.test` | `201` |
| 5 | [05-confirmar-sin-recibir.md](05-confirmar-sin-recibir.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<PENDIENTE>/confirmation` | `compras.test` | `200` |
| 6 | [06-anular-sin-recibir.md](06-anular-sin-recibir.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<PENDIENTE>/cancellation` | `compras.test` | `200` |
| 7 | [07-compra-a-anular.md](07-compra-a-anular.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases` | `compras.test` | `201` |
| 8 | [08-confirmar.md](08-confirmar.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/confirmation` | `compras.test` | `200` |
| 9 | [09-recibir.md](09-recibir.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/receipt` | `compras.test` | `200` |
| 10 | [10-anular-la-compra-recibida.md](10-anular-la-compra-recibida.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/cancellation` | `compras.test` | `200` |
| 11 | [11-compra-vendida.md](11-compra-vendida.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases` | `compras.test` | `201` |
| 12 | [12-confirmar-la-otra.md](12-confirmar-la-otra.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<VENDIDA>/confirmation` | `compras.test` | `200` |
| 13 | [13-recibir-la-otra.md](13-recibir-la-otra.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<VENDIDA>/receipt` | `compras.test` | `200` |
| 14 | [14-anular-con-inventario-consumido.md](14-anular-con-inventario-consumido.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<VENDIDA>/cancellation` | `compras.test` | `409` |

## Por qué este orden

- La numeración necesita una secuencia activa antes de confirmar; la confirmación necesita un borrador; la anulación y los hitos de recepción necesitan una compra confirmada.

## Variables

| Variable | Se guarda en | Se usa en |
| --- | --- | --- |
| `<SECUENCIA>` | paso 1 (`id`) | pasos — |
| `<BORRADOR>` | paso 2 (`id`) | pasos 3 |
| `<PENDIENTE>` | paso 4 (`id`) | pasos 5, 6 |
| `<VERSION_PENDIENTE>` | paso 5 (`version`) | pasos 6 |
| `<COMPRA>` | paso 7 (`id`) | pasos 8, 9, 10 |
| `<VERSION_COMPRA>` | paso 8 (`version`) | pasos 9 |
| `<ENTRADA>` | paso 9 (`inventory_operation_id`) | pasos — |
| `<VERSION_RECIBIDA>` | paso 9 (`version`) | pasos 10 |
| `<VENDIDA>` | paso 11 (`id`) | pasos 12, 13, 14 |
| `<VERSION_VENDIDA>` | paso 12 (`version`) | pasos 13 |
| `<ENTRADA_VENDIDA>` | paso 13 (`inventory_operation_id`) | pasos — |
| `<VERSION_VENDIDA_RECIBIDA>` | paso 13 (`version`) | pasos 14 |
