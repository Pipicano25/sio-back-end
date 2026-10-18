# Ejercicio 3: Inventario multisucursal

Existencias de la Loratadina en toda la empresa y en una sucursal sin usuarios asignados: unidad base, equivalencias por presentación y diferencia entre saldo cero y sin registro.

Datos **ficticios** (ver `00-datos-ficticios.md`). El ejercicio es independiente y solo consulta: no cambia ningún dato.

## Orden de los pasos

| Paso | Archivo | Llamada | Ejecuta | Estado |
| --- | --- | --- | --- | --- |
| 1 | [01-consolidado.md](01-consolidado.md) | `GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/inventory-overviews?search=Loratadina` | `inventario.test` | `200` |
| 2 | [02-sucursal-no-asignada.md](02-sucursal-no-asignada.md) | `GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/inventory-overviews?search=Loratadina&branch_id=d22b0000-0000-4000-8000-000000000002` | `inventario.test` | `200` |
| 3 | [03-sucursal-de-otra-empresa.md](03-sucursal-de-otra-empresa.md) | `GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/inventory-overviews?branch_id=d22b0000-0000-4000-8000-000000000099` | `inventario.test` | `404` |
