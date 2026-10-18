# Ejercicio 6: Permisos y bloques visibles

La misma consulta muestra bloques distintos según los permisos: `ventas` sin mínimos, `inventario` sin precios, y `compras`, `reportes` y `consulta` sin acceso.

Datos **ficticios** (ver `00-datos-ficticios.md`). El ejercicio es independiente y solo consulta: no cambia ningún dato.

## Orden de los pasos

| Paso | Archivo | Llamada | Ejecuta | Estado |
| --- | --- | --- | --- | --- |
| 1 | [01-ventas-sin-minimos.md](01-ventas-sin-minimos.md) | `GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/product-overviews?search=Loratadina` | `ventas.test` | `200` |
| 2 | [02-inventario-sin-precios.md](02-inventario-sin-precios.md) | `GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/product-overviews?search=Loratadina` | `inventario.test` | `200` |
| 3 | [03-filtro-no-autorizado.md](03-filtro-no-autorizado.md) | `GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/inventory-overviews?minimum_state=BELOW_MINIMUM` | `ventas.test` | `403` |
| 4 | [04-compras-sin-acceso.md](04-compras-sin-acceso.md) | `GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/inventory-summary` | `compras.test` | `403` |
