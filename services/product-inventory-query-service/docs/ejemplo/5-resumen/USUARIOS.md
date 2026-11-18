# Usuarios del ejercicio 5

| Usuario | Paso 1 | Paso 2 |
| --- | --- | --- |
| `admin.sio` | `200` | `200` |
| `admin.dao` | `200` | `200` |
| `operario.dao` | `200` | `200` |

## Permiso por URL

| Paso | URL | Permiso |
| --- | --- | --- |
| 1 | `GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/inventory-summary` | `perm:product-inventory-query:inventory_summary:read` |
| 2 | `GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/inventory-summary?branch_id=d22b0000-0000-4000-8000-000000000002` | `perm:product-inventory-query:inventory_summary:read` |

## Ejemplos

- Puede: `operario.dao` (grupos `Compras`, `Ventas` e `Inventario`) consulta las cuatro rutas con precios, existencias y mínimos; `admin.dao` (grupo `admin`) y `admin.sio` (grupo `superadmin`) también.
- No puede: un usuario sin los permisos de estas consultas recibe `403` (ningún usuario de prueba del realm está en ese caso desde la spec 026).
