# Usuarios del ejercicio 3

| Usuario | Paso 1 | Paso 2 | Paso 3 |
| --- | --- | --- | --- |
| `admin.test` | `200` | `200` | `404` |
| `supervisor.test` | `200` | `200` | `404` |
| `compras.test` | `403` | `403` | `403` |
| `ventas.test` | `200` | `200` | `404` |
| `inventario.test` | `200` | `200` | `404` |
| `reportes.test` | `403` | `403` | `403` |
| `consulta.test` | `403` | `403` | `403` |

## Permiso por URL

| Paso | URL | Permiso |
| --- | --- | --- |
| 1 | `GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/inventory-overviews?search=Loratadina` | `perm:product-inventory-query:inventory_overviews:read` |
| 2 | `GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/inventory-overviews?search=Loratadina&branch_id=d22b0000-0000-4000-8000-000000000002` | `perm:product-inventory-query:inventory_overviews:read` |
| 3 | `GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/inventory-overviews?branch_id=d22b0000-0000-4000-8000-000000000099` | `perm:product-inventory-query:inventory_overviews:read` |

## Ejemplos

- Puede: `ventas.test` consulta productos e inventario (con precios y existencias, sin mínimos); `inventario.test` consulta las cuatro (con existencias y mínimos, sin precios); `supervisor.test` y `admin.test` ven todos los bloques.
- No puede: `compras.test`, `reportes.test` y `consulta.test` reciben `403` en las cuatro consultas.
