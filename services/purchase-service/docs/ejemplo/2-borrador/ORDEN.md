# Ejercicio 2: Compra en borrador

El comprador registra una compra en borrador con una línea en caja de 12, agrega otra línea, y ve los rechazos de versión vieja, de producto sin control de inventario y de proveedor inexistente.

Datos **ficticios** (ver `00-datos-ficticios.md`). El ejercicio es independiente: se ejecuta en una base nueva con el reloj fijo en el 5 de noviembre de 2026.

## Orden de los pasos

| Paso | Archivo | Llamada | Ejecuta | Estado |
| --- | --- | --- | --- | --- |
| 1 | [01-crear-el-borrador.md](01-crear-el-borrador.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases` | `compras.test` | `201` |
| 2 | [02-agregar-una-linea.md](02-agregar-una-linea.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/details` | `compras.test` | `201` |
| 3 | [03-version-vieja.md](03-version-vieja.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/details` | `compras.test` | `409` |
| 4 | [04-producto-sin-control-de-inventario.md](04-producto-sin-control-de-inventario.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/details` | `compras.test` | `409` |
| 5 | [05-proveedor-inexistente.md](05-proveedor-inexistente.md) | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases` | `compras.test` | `422` |
| 6 | [06-consultar-el-borrador.md](06-consultar-el-borrador.md) | `GET /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>` | `compras.test` | `200` |

## Por qué este orden

- La numeración necesita una secuencia activa antes de confirmar; la confirmación necesita un borrador; la anulación y los hitos de recepción necesitan una compra confirmada.

## Variables

| Variable | Se guarda en | Se usa en |
| --- | --- | --- |
| `<COMPRA>` | paso 1 (`id`) | pasos 2, 3, 4, 6 |
