# Ejercicio 5: Resumen de inventario

Indicadores operativos por sucursal y consolidados, cada uno calculado por su propietario: los adoptados por Commercial Relationship y los de saldo y política por Inventory. El resumen no tiene valoración económica (fuera del alcance de la spec 022).

Datos **ficticios** (ver `00-datos-ficticios.md`). El ejercicio es independiente y solo consulta: no cambia ningún dato.

## Orden de los pasos

| Paso | Archivo | Llamada | Ejecuta | Estado |
| --- | --- | --- | --- | --- |
| 1 | [01-resumen-de-la-empresa.md](01-resumen-de-la-empresa.md) | `GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/inventory-summary` | `inventario.test` | `200` |
| 2 | [02-resumen-de-una-sucursal.md](02-resumen-de-una-sucursal.md) | `GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/inventory-summary?branch_id=d22b0000-0000-4000-8000-000000000002` | `supervisor.test` | `200` |
