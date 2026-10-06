# Ejercicio 1: Entradas de compra

Purchase confirma una compra y aplica su entrada en Inventory con su identidad técnica: una entrada de dos líneas con costo, su repetición idempotente, una clave reutilizada con otro contenido y un producto sin control de inventario.

Datos **ficticios** (ver `00-datos-ficticios.md`). El ejercicio es independiente: se ejecuta en una base nueva.

## Orden de los pasos

| Paso | Archivo | Llamada | Ejecuta | Estado |
| --- | --- | --- | --- | --- |
| 1 | [01-aplicar-una-entrada.md](01-aplicar-una-entrada.md) | `POST /api/v1/inventory-entries` | `inventory-test-operator` (cuenta de servicio) | `201` |
| 2 | [02-repetir-la-entrada.md](02-repetir-la-entrada.md) | `POST /api/v1/inventory-entries` | `inventory-test-operator` (cuenta de servicio) | `200` |
| 3 | [03-misma-clave-otra-cantidad.md](03-misma-clave-otra-cantidad.md) | `POST /api/v1/inventory-entries` | `inventory-test-operator` (cuenta de servicio) | `409` |
| 4 | [04-producto-sin-control-de-inventario.md](04-producto-sin-control-de-inventario.md) | `POST /api/v1/inventory-entries` | `inventory-test-operator` (cuenta de servicio) | `422` |

## Por qué este orden

- Los saldos nacen de las entradas: las entradas van primero; las salidas, reversos y consultas dependen del saldo que dejan los pasos anteriores.

## Variables

| Variable | Se guarda en | Se usa en |
| --- | --- | --- |
| `<OP_ENTRADA>` | paso 1 (`id`) | pasos — |
