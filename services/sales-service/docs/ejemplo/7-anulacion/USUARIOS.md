# Usuarios del ejercicio 7

| Usuario | Paso 1 | Paso 2 | Paso 3 | Paso 4 | Paso 5 | Paso 6 |
| --- | --- | --- | --- | --- | --- | --- |
| `admin.sio` | `—` | `—` | `—` | `—` | `—` | `—` |
| `admin.dao` | `—` | `—` | `—` | `—` | `—` | `—` |
| `operario.dao` | `201` | `201` | `200` | `201` | `200` | `200` |

## Permiso por URL

| Paso | URL | Permiso |
| --- | --- | --- |
| 1 | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sale-sequences` | `perm:sales:sale_sequences:create` |
| 2 | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales` | `perm:sales:sales:create` |
| 3 | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<BORRADOR>/cancellation` | `perm:sales:sales:delete` |
| 4 | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales` | `perm:sales:sales:create` |
| 5 | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/confirmation` | `perm:sales:sales:update` |
| 6 | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/cancellation` | `perm:sales:sales:delete` |

## Ejemplos

- Puede: `operario.dao` (grupos `Compras`, `Ventas` e `Inventario`, `perm:sales:all:create|read|update|delete`) registran, confirman y anulan ventas de las sucursales asignadas, **sin** ver costo ni margen; `admin.dao` (grupo `admin`, `perm:sales:all:all`) también, y ve la rentabilidad; `admin.sio` (grupo `superadmin`) por comodín, con rentabilidad.
- No puede: ninguna cuenta de servicio escribe ventas (ni el propio `sales-service`); el operario (`Compras`, `Ventas` e `Inventario`) no ve la rentabilidad; sin asignación a la sucursal, ni el comodín permite escribir.
