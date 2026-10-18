# Orden del ejercicio 4: Evolución de existencias de una sucursal

- Pasos independientes: primero la sucursal principal (su UUID va en la ruta) y después la empresa consolidada.

| Paso | Archivo | Llamada |
| --- | --- | --- |
| 1 | [01-sucursal-principal.md](01-sucursal-principal.md) | `GET /api/v1/companies/d23a0000-0000-4000-8000-000000000001/branches/d23b0000-0000-4000-8000-000000000001/reports/stock-evolution?date_from=2026-10-01&date_to=2026-10-15` |
| 2 | [02-consolidada-de-la-empresa.md](02-consolidada-de-la-empresa.md) | `GET /api/v1/companies/d23a0000-0000-4000-8000-000000000001/reports/stock-evolution?date_from=2026-10-01&date_to=2026-10-15` |

No se guardan variables entre pasos: todos usan los identificadores fijos de los datos.
