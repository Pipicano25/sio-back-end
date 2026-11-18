# Usuarios del ejercicio 2

| Usuario | Paso 1 | Paso 2 | Paso 3 | Paso 4 | Paso 5 | Paso 6 | Paso 7 | Paso 8 | Paso 9 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `admin.sio` | `—` | `—` | `—` | `—` | `—` | `—` | `—` | `—` | `200` |
| `admin.dao` | `—` | `—` | `—` | `—` | `—` | `—` | `—` | `—` | `200` |
| `operario.dao` | `201` | `201` | `422` | `422` | `422` | `409` | `409` | `409` | `200` |

## Permiso por URL

| Paso | URL | Permiso |
| --- | --- | --- |
| 1 | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales` | `perm:sales:sales:create` |
| 2 | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/details` | `perm:sales:sale_details:create` |
| 3 | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/details` | `perm:sales:sale_details:create` |
| 4 | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/details` | `perm:sales:sale_details:create` |
| 5 | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/details` | `perm:sales:sale_details:create` |
| 6 | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/details` | `perm:sales:sale_details:create` |
| 7 | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/details` | `perm:sales:sale_details:create` |
| 8 | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/details` | `perm:sales:sale_details:create` |
| 9 | `GET /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>` | `perm:sales:sales:read` |

## Ejemplos

- Puede: `operario.dao` (grupos `Compras`, `Ventas` e `Inventario`, `perm:sales:all:create|read|update|delete`) registran, confirman y anulan ventas de las sucursales asignadas, **sin** ver costo ni margen; `admin.dao` (grupo `admin`, `perm:sales:all:all`) también, y ve la rentabilidad; `admin.sio` (grupo `superadmin`) por comodín, con rentabilidad.
- No puede: ninguna cuenta de servicio escribe ventas (ni el propio `sales-service`); el operario (`Compras`, `Ventas` e `Inventario`) no ve la rentabilidad; sin asignación a la sucursal, ni el comodín permite escribir.
