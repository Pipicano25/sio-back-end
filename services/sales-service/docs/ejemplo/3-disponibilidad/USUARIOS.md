# Usuarios del ejercicio 3

| Usuario | Paso 1 | Paso 2 |
| --- | --- | --- |
| `admin.test` | `—` | `200` |
| `supervisor.test` | `—` | `200` |
| `compras.test` | `—` | `200` |
| `ventas.test` | `201` | `200` |
| `inventario.test` | `—` | `200` |

## Permiso por URL

| Paso | URL | Permiso |
| --- | --- | --- |
| 1 | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales` | `perm:sales:sales:create` |
| 2 | `GET /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/availability` | `perm:sales:sales:read` |

## Ejemplos

- Puede: `ventas.test`, `compras.test` e `inventario.test` (grupo `empleado`, `perm:sales:all:create|read|update|delete`) registran, confirman y anulan ventas de las sucursales asignadas, **sin** ver costo ni margen; `supervisor.test` (grupo `admin`, `perm:sales:all:all`) también, y ve la rentabilidad; `admin.test` (grupo `superadmin`) por comodín, con rentabilidad.
- No puede: ninguna cuenta de servicio escribe ventas (ni el propio `sales-service`); el grupo `empleado` no ve la rentabilidad; sin asignación a la sucursal, ni el comodín permite escribir.
