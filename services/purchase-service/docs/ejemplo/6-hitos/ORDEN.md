# Ejercicio 6: Hitos logísticos

El comprador registra los hitos de abastecimiento, ve el rechazo de un hito fuera de orden y consulta la línea de tiempo con los intervalos y el lead time total.

Datos **ficticios** (ver `00-datos-ficticios.md`). El ejercicio es independiente: se ejecuta en una base nueva con el reloj fijo en el 5 de noviembre de 2026.

## Orden de los pasos

| Paso | Archivo | Llamada | Ejecuta | Estado |
| --- | --- | --- | --- | --- |
| 1 | [01-crear-la-secuencia.md](01-crear-la-secuencia.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchase-sequences` | `compras.test` | `201` |
| 2 | [02-crear-la-compra.md](02-crear-la-compra.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases` | `compras.test` | `201` |
| 3 | [03-pedido.md](03-pedido.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/lifecycle-events` | `compras.test` | `201` |
| 4 | [04-llegada-fuera-de-orden.md](04-llegada-fuera-de-orden.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/lifecycle-events` | `compras.test` | `422` |
| 5 | [05-despacho.md](05-despacho.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/lifecycle-events` | `compras.test` | `201` |
| 6 | [06-llegada.md](06-llegada.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/lifecycle-events` | `compras.test` | `201` |
| 7 | [07-confirmar.md](07-confirmar.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/confirmation` | `compras.test` | `200` |
| 8 | [07a-hito-sin-recepcion.md](07a-hito-sin-recepcion.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/lifecycle-events` | `compras.test` | `409` |
| 9 | [07b-recibir.md](07b-recibir.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/receipt` | `compras.test` | `200` |
| 10 | [08-recepcion.md](08-recepcion.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/lifecycle-events` | `compras.test` | `201` |
| 11 | [09-disponible.md](09-disponible.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/lifecycle-events` | `compras.test` | `201` |
| 12 | [10-linea-de-tiempo.md](10-linea-de-tiempo.md) | `GET /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/lifecycle-events` | `compras.test` | `200` |

## Por qué este orden

- La numeración necesita una secuencia activa antes de confirmar; la confirmación necesita un borrador; la anulación y los hitos de recepción necesitan una compra confirmada.

## Variables

| Variable | Se guarda en | Se usa en |
| --- | --- | --- |
| `<SECUENCIA>` | paso 1 (`id`) | pasos — |
| `<COMPRA>` | paso 2 (`id`) | pasos 3, 4, 5, 6, 7, 8, 9, 10, 11, 12 |
| `<VERSION_COMPRA>` | paso 7 (`version`) | pasos 9 |
