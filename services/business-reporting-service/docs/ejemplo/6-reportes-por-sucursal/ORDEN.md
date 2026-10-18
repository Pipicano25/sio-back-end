# Orden del ejercicio 6: Reportes de una sucursal

- Pasos independientes: las rutas `/branches/{branch_id}/reports/…` consultan solo esa sucursal.

| Paso | Archivo | Llamada |
| --- | --- | --- |
| 1 | [01-ventas-de-la-sucursal.md](01-ventas-de-la-sucursal.md) | `GET /api/v1/companies/d23a0000-0000-4000-8000-000000000001/branches/d23b0000-0000-4000-8000-000000000002/reports/sales-by-branch?date_from=2026-10-01&date_to=2026-10-15` |
| 2 | [02-compras-de-la-sucursal.md](02-compras-de-la-sucursal.md) | `GET /api/v1/companies/d23a0000-0000-4000-8000-000000000001/branches/d23b0000-0000-4000-8000-000000000002/reports/purchases?date_from=2026-10-01&date_to=2026-10-15` |

No se guardan variables entre pasos: todos usan los identificadores fijos de los datos.
