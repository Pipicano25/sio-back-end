# Ejercicio 2: Salidas de venta

Sales confirma una venta y aplica su salida: una salida con saldo suficiente, una salida rechazada por saldo insuficiente (sin aplicar ninguna línea) y una salida con costo.

Datos **ficticios** (ver `00-datos-ficticios.md`). El ejercicio es independiente: se ejecuta en una base nueva.

## Orden de los pasos

| Paso | Archivo | Llamada | Ejecuta | Estado |
| --- | --- | --- | --- | --- |
| 1 | [01-entrada-inicial.md](01-entrada-inicial.md) | `POST /api/v1/inventory-entries` | `inventory-test-operator` (cuenta de servicio) | `201` |
| 2 | [02-aplicar-una-salida.md](02-aplicar-una-salida.md) | `POST /api/v1/inventory-outputs` | `inventory-test-operator` (cuenta de servicio) | `201` |
| 3 | [03-saldo-insuficiente.md](03-saldo-insuficiente.md) | `POST /api/v1/inventory-outputs` | `inventory-test-operator` (cuenta de servicio) | `409` |
| 4 | [04-salida-con-costo.md](04-salida-con-costo.md) | `POST /api/v1/inventory-outputs` | `inventory-test-operator` (cuenta de servicio) | `422` |

## Por qué este orden

- Los saldos nacen de las entradas: las entradas van primero; las salidas, reversos y consultas dependen del saldo que dejan los pasos anteriores.
