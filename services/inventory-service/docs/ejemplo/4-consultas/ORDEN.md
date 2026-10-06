# Ejercicio 4: Consultas de stock y kardex

Los usuarios autorizados consultan el saldo de un producto, el stock de la sucursal, saldos por lote, el kardex y una operación por su clave; fuera de su empresa reciben `404`.

Datos **ficticios** (ver `00-datos-ficticios.md`). El ejercicio es independiente: se ejecuta en una base nueva.

## Orden de los pasos

| Paso | Archivo | Llamada | Ejecuta | Estado |
| --- | --- | --- | --- | --- |
| 1 | [01-entrada.md](01-entrada.md) | `POST /api/v1/inventory-entries` | `inventory-test-operator` (cuenta de servicio) | `201` |
| 2 | [02-salida.md](02-salida.md) | `POST /api/v1/inventory-outputs` | `inventory-test-operator` (cuenta de servicio) | `201` |
| 3 | [03-saldo-de-un-producto.md](03-saldo-de-un-producto.md) | `GET /api/v1/companies/d44a0000-0000-4000-8000-000000000001/branches/d44b0000-0000-4000-8000-000000000001/balances/d44d0000-0000-4000-8000-000000000001` | `inventario.test` | `200` |
| 4 | [04-stock-de-la-sucursal.md](04-stock-de-la-sucursal.md) | `GET /api/v1/companies/d44a0000-0000-4000-8000-000000000001/branches/d44b0000-0000-4000-8000-000000000001/balances?in_stock_only=true` | `inventario.test` | `200` |
| 5 | [05-saldos-por-lote.md](05-saldos-por-lote.md) | `POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/branches/d44b0000-0000-4000-8000-000000000001/balances/lookup` | `inventario.test` | `200` |
| 6 | [06-kardex.md](06-kardex.md) | `GET /api/v1/companies/d44a0000-0000-4000-8000-000000000001/branches/d44b0000-0000-4000-8000-000000000001/kardex/d44d0000-0000-4000-8000-000000000001` | `inventario.test` | `200` |
| 7 | [07-operacion-por-clave.md](07-operacion-por-clave.md) | `GET /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-operations/by-key/d44f0100-0000-4000-8000-000000000001` | `inventario.test` | `200` |
| 8 | [08-empresa-sin-membresia.md](08-empresa-sin-membresia.md) | `GET /api/v1/companies/d44a0000-0000-4000-8000-000000000099/branches/d44b0000-0000-4000-8000-000000000001/balances` | `inventario.test` | `404` |

## Por qué este orden

- Los saldos nacen de las entradas: las entradas van primero; las salidas, reversos y consultas dependen del saldo que dejan los pasos anteriores.
