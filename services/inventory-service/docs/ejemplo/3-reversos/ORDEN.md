# Ejercicio 3: Reversos

Purchase y Sales anulan documentos confirmados revirtiendo la operación completa con `company_id` obligatorio: reverso de una entrada sin saldo suficiente, reverso de una salida, reverso repetido y reverso pedido desde otra empresa.

Datos **ficticios** (ver `00-datos-ficticios.md`). El ejercicio es independiente: se ejecuta en una base nueva.

## Orden de los pasos

| Paso | Archivo | Llamada | Ejecuta | Estado |
| --- | --- | --- | --- | --- |
| 1 | [01-entrada.md](01-entrada.md) | `POST /api/v1/inventory-entries` | `inventory-test-operator` (cuenta de servicio) | `201` |
| 2 | [02-salida.md](02-salida.md) | `POST /api/v1/inventory-outputs` | `inventory-test-operator` (cuenta de servicio) | `201` |
| 3 | [03-reverso-de-entrada-sin-saldo.md](03-reverso-de-entrada-sin-saldo.md) | `POST /api/v1/inventory-entries/<OP_ENTRADA>/reversal` | `inventory-test-operator` (cuenta de servicio) | `409` |
| 4 | [04-reverso-de-salida.md](04-reverso-de-salida.md) | `POST /api/v1/inventory-outputs/<OP_SALIDA>/reversal` | `inventory-test-operator` (cuenta de servicio) | `201` |
| 5 | [05-reverso-repetido.md](05-reverso-repetido.md) | `POST /api/v1/inventory-outputs/<OP_SALIDA>/reversal` | `inventory-test-operator` (cuenta de servicio) | `409` |
| 6 | [06-reverso-desde-otra-empresa.md](06-reverso-desde-otra-empresa.md) | `POST /api/v1/inventory-entries/<OP_ENTRADA>/reversal` | `inventory-test-operator` (cuenta de servicio) | `404` |
| 7 | [07-reverso-de-entrada.md](07-reverso-de-entrada.md) | `POST /api/v1/inventory-entries/<OP_ENTRADA>/reversal` | `inventory-test-operator` (cuenta de servicio) | `201` |

## Por qué este orden

- Los saldos nacen de las entradas: las entradas van primero; las salidas, reversos y consultas dependen del saldo que dejan los pasos anteriores.

## Variables

| Variable | Se guarda en | Se usa en |
| --- | --- | --- |
| `<OP_ENTRADA>` | paso 1 (`id`) | pasos 3, 6, 7 |
| `<OP_SALIDA>` | paso 2 (`id`) | pasos 4, 5 |
