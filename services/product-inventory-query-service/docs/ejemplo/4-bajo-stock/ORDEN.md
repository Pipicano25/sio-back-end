# Ejercicio 4: Productos bajo el mínimo

Pares producto–sucursal con existencia estrictamente menor que el mínimo activo, del mayor faltante al menor. Igual al mínimo, mínimo 0 y sin política no aparecen.

Datos **ficticios** (ver `00-datos-ficticios.md`). El ejercicio es independiente y solo consulta: no cambia ningún dato.

## Orden de los pasos

| Paso | Archivo | Llamada | Ejecuta | Estado |
| --- | --- | --- | --- | --- |
| 1 | [01-todas-las-sucursales.md](01-todas-las-sucursales.md) | `GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/low-stock-products` | `inventario.test` | `200` |
| 2 | [02-una-sucursal.md](02-una-sucursal.md) | `GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/low-stock-products?branch_id=d22b0000-0000-4000-8000-000000000002` | `inventario.test` | `200` |
