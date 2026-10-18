# Orden del ejercicio 3: Compras del período

- Primero todas las compras con sus totales; después solo las pendientes: los totales no cambian porque son del período completo.

| Paso | Archivo | Llamada |
| --- | --- | --- |
| 1 | [01-compras-y-totales.md](01-compras-y-totales.md) | `GET /api/v1/companies/d23a0000-0000-4000-8000-000000000001/reports/purchases?date_from=2026-10-01&date_to=2026-10-15` |
| 2 | [02-solo-pendientes.md](02-solo-pendientes.md) | `GET /api/v1/companies/d23a0000-0000-4000-8000-000000000001/reports/purchases?date_from=2026-10-01&date_to=2026-10-15&category=PENDING_RECEIPT` |

No se guardan variables entre pasos: todos usan los identificadores fijos de los datos.
