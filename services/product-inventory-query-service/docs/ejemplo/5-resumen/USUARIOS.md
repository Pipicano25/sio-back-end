# Usuarios del ejercicio 5

| Usuario | Paso 1 | Paso 2 |
| --- | --- | --- |
| `admin.test` | `200` | `200` |
| `supervisor.test` | `200` | `200` |
| `compras.test` | `200` | `200` |
| `ventas.test` | `200` | `200` |
| `inventario.test` | `200` | `200` |

## Permiso por URL

| Paso | URL | Permiso |
| --- | --- | --- |
| 1 | `GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/inventory-summary` | `perm:product-inventory-query:inventory_summary:read` |
| 2 | `GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/inventory-summary?branch_id=d22b0000-0000-4000-8000-000000000002` | `perm:product-inventory-query:inventory_summary:read` |

## Ejemplos

- Puede: `ventas.test`, `compras.test` e `inventario.test` (grupo `empleado`) consultan las cuatro rutas con precios, existencias y mínimos; `supervisor.test` (grupo `admin`) y `admin.test` (grupo `superadmin`) también.
- No puede: un usuario sin los permisos de estas consultas recibe `403` (ningún usuario de prueba del realm está en ese caso desde la spec 026).
