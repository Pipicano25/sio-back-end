# Orden del ejercicio 1: Productos más vendidos

- Primero el ranking predeterminado (por cantidad) y después por importe con el desglose por presentación: son independientes.

| Paso | Archivo | Llamada |
| --- | --- | --- |
| 1 | [01-ranking-por-cantidad.md](01-ranking-por-cantidad.md) | `GET /api/v1/companies/d23a0000-0000-4000-8000-000000000001/reports/top-selling-products?date_from=2026-10-01&date_to=2026-10-15` |
| 2 | [02-ranking-por-importe.md](02-ranking-por-importe.md) | `GET /api/v1/companies/d23a0000-0000-4000-8000-000000000001/reports/top-selling-products?date_from=2026-10-01&date_to=2026-10-15&rank_by=amount&include_presentations=true&limit=2` |

No se guardan variables entre pasos: todos usan los identificadores fijos de los datos.
