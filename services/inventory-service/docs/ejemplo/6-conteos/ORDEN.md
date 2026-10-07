# Ejercicio 6: Conteos físicos

Un conteo completo con faltante y sobrante que se aplica como una sola operación de ajustes, un conteo cuya finalización dejaría un saldo negativo (no aplica nada) y su cancelación.

Datos **ficticios** (ver `00-datos-ficticios.md`). El ejercicio es independiente: se ejecuta en una base nueva.

## Orden de los pasos

| Paso | Archivo | Llamada | Ejecuta | Estado |
| --- | --- | --- | --- | --- |
| 1 | [01-entrada.md](01-entrada.md) | `POST /api/v1/inventory-entries` | `inventory-test-operator` (cuenta de servicio) | `201` |
| 2 | [02-crear-conteo.md](02-crear-conteo.md) | `POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-counts` | `inventario.test` | `201` |
| 3 | [03-iniciar.md](03-iniciar.md) | `POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-counts/<CONTEO>/start` | `inventario.test` | `200` |
| 4 | [04-contar-arroz.md](04-contar-arroz.md) | `PUT /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-counts/<CONTEO>/details/d44d0000-0000-4000-8000-000000000001` | `inventario.test` | `200` |
| 5 | [05-contar-aceite.md](05-contar-aceite.md) | `PUT /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-counts/<CONTEO>/details/d44d0000-0000-4000-8000-000000000002` | `inventario.test` | `200` |
| 6 | [06-completar.md](06-completar.md) | `POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-counts/<CONTEO>/complete` | `inventario.test` | `200` |
| 7 | [07-consultar.md](07-consultar.md) | `GET /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-counts/<CONTEO>` | `inventario.test` | `200` |
| 8 | [08-segundo-conteo.md](08-segundo-conteo.md) | `POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-counts` | `inventario.test` | `201` |
| 9 | [09-iniciar-segundo.md](09-iniciar-segundo.md) | `POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-counts/<CONTEO_2>/start` | `inventario.test` | `200` |
| 10 | [10-contar-arroz-cero.md](10-contar-arroz-cero.md) | `PUT /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-counts/<CONTEO_2>/details/d44d0000-0000-4000-8000-000000000001` | `inventario.test` | `200` |
| 11 | [11-venta-intermedia.md](11-venta-intermedia.md) | `POST /api/v1/inventory-outputs` | `inventory-test-operator` (cuenta de servicio) | `201` |
| 12 | [12-completar-con-saldo-insuficiente.md](12-completar-con-saldo-insuficiente.md) | `POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-counts/<CONTEO_2>/complete` | `inventario.test` | `409` |
| 13 | [13-cancelar.md](13-cancelar.md) | `POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-counts/<CONTEO_2>/cancel` | `inventario.test` | `200` |

## Por qué este orden

- Los saldos nacen de las entradas: las entradas van primero; las salidas, reversos y consultas dependen del saldo que dejan los pasos anteriores.

## Variables

| Variable | Se guarda en | Se usa en |
| --- | --- | --- |
| `<CONTEO>` | paso 2 (`id`) | pasos 3, 4, 5, 6, 7 |
| `<CONTEO_2>` | paso 8 (`id`) | pasos 9, 10, 12, 13 |
