# Ejercicio 5: Ajustes de inventario

Un usuario de la bodega, asignado a la sucursal, corrige el inventario con ajustes que se aplican al registrarlos: un ajuste negativo valorizado con FIFO, uno positivo con el costo de la capa más reciente, uno positivo de un producto sin capas (costo obligatorio) y un ajuste en una sucursal a la que el usuario no está asignado.

Datos **ficticios** (ver `00-datos-ficticios.md`). El ejercicio es independiente: se ejecuta en una base nueva.

## Orden de los pasos

| Paso | Archivo | Llamada | Ejecuta | Estado |
| --- | --- | --- | --- | --- |
| 1 | [01-entrada.md](01-entrada.md) | `POST /api/v1/inventory-entries` | `inventory-test-operator` (cuenta de servicio) | `201` |
| 2 | [02-ajuste-negativo.md](02-ajuste-negativo.md) | `POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-adjustments` | `inventario.test` | `201` |
| 3 | [03-ajuste-positivo.md](03-ajuste-positivo.md) | `POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-adjustments` | `inventario.test` | `201` |
| 4 | [04-ajuste-positivo-sin-capas.md](04-ajuste-positivo-sin-capas.md) | `POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-adjustments` | `inventario.test` | `422` |
| 5 | [05-ajuste-positivo-con-costo.md](05-ajuste-positivo-con-costo.md) | `POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-adjustments` | `inventario.test` | `201` |
| 6 | [06-sucursal-no-asignada.md](06-sucursal-no-asignada.md) | `POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-adjustments` | `inventario.test` | `403` |
| 7 | [07-consultar-el-ajuste.md](07-consultar-el-ajuste.md) | `GET /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-adjustments/<AJUSTE>` | `inventario.test` | `200` |

## Por qué este orden

- Los saldos nacen de las entradas: las entradas van primero; las salidas, reversos y consultas dependen del saldo que dejan los pasos anteriores.

## Variables

| Variable | Se guarda en | Se usa en |
| --- | --- | --- |
| `<AJUSTE>` | paso 2 (`id`) | pasos 7 |
