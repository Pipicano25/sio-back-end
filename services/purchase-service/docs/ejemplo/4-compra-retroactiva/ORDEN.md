# Ejercicio 4: Compra retroactiva

Con numeración mensual, una compra de octubre confirmada en noviembre continúa el contador de octubre en lugar de rechazarse.

Datos **ficticios** (ver `00-datos-ficticios.md`). El ejercicio es independiente: se ejecuta en una base nueva con el reloj fijo en el 5 de noviembre de 2026.

## Orden de los pasos

| Paso | Archivo | Llamada | Ejecuta | Estado |
| --- | --- | --- | --- | --- |
| 1 | [01-crear-la-secuencia.md](01-crear-la-secuencia.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchase-sequences` | `compras.test` | `201` |
| 2 | [02-compra-de-noviembre.md](02-compra-de-noviembre.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases` | `compras.test` | `201` |
| 3 | [03-confirmar-noviembre.md](03-confirmar-noviembre.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<NOVIEMBRE>/confirmation` | `compras.test` | `200` |
| 4 | [04-compra-de-octubre.md](04-compra-de-octubre.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases` | `compras.test` | `201` |
| 5 | [05-confirmar-octubre.md](05-confirmar-octubre.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<OCTUBRE>/confirmation` | `compras.test` | `200` |

## Por qué este orden

- La numeración necesita una secuencia activa antes de confirmar; la confirmación necesita un borrador; la anulación y los hitos de recepción necesitan una compra confirmada.

## Variables

| Variable | Se guarda en | Se usa en |
| --- | --- | --- |
| `<SECUENCIA>` | paso 1 (`id`) | pasos — |
| `<NOVIEMBRE>` | paso 2 (`id`) | pasos 3 |
| `<OCTUBRE>` | paso 4 (`id`) | pasos 5 |
