# Usuarios del ejercicio 6

| Usuario | Paso 1 | Paso 2 | Paso 3 | Paso 4 | Paso 5 | Paso 6 | Paso 7 | Paso 8 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `admin.test` | `—` | `—` | `—` | `200` | `200` | `—` | `—` | `200` |
| `supervisor.test` | `—` | `—` | `—` | `200` | `200` | `—` | `—` | `200` |
| `compras.test` | `—` | `—` | `—` | `200` | `200` | `—` | `—` | `200` |
| `ventas.test` | `201` | `201` | `200` | `200` | `200` | `201` | `200` | `200` |
| `inventario.test` | `—` | `—` | `—` | `200` | `200` | `—` | `—` | `200` |

## Permiso por URL

| Paso | URL | Permiso |
| --- | --- | --- |
| 1 | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sale-sequences` | `perm:sales:sale_sequences:create` |
| 2 | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales` | `perm:sales:sales:create` |
| 3 | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/confirmation` | `perm:sales:sales:update` |
| 4 | `GET /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>` | `perm:sales:sales:read` |
| 5 | `GET /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>` | `perm:sales:sales:read` |
| 6 | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales` | `perm:sales:sales:create` |
| 7 | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<APERTURA>/confirmation` | `perm:sales:sales:update` |
| 8 | `GET /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<APERTURA>` | `perm:sales:sales:read` |

## Ejemplos

- Puede: `ventas.test`, `compras.test` e `inventario.test` (grupo `empleado`, `perm:sales:all:create|read|update|delete`) registran, confirman y anulan ventas de las sucursales asignadas, **sin** ver costo ni margen; `supervisor.test` (grupo `admin`, `perm:sales:all:all`) también, y ve la rentabilidad; `admin.test` (grupo `superadmin`) por comodín, con rentabilidad.
- No puede: ninguna cuenta de servicio escribe ventas (ni el propio `sales-service`); el grupo `empleado` no ve la rentabilidad; sin asignación a la sucursal, ni el comodín permite escribir.
