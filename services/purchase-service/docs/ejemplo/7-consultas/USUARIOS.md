# Usuarios del ejercicio 7

| Usuario | Paso 1 | Paso 2 | Paso 3 | Paso 4 | Paso 5 |
| --- | --- | --- | --- | --- | --- |
| `admin.sio` | `—` | `—` | `—` | `200` | `404` |
| `admin.dao` | `—` | `—` | `—` | `200` | `404` |
| `operario.dao` | `201` | `201` | `200` | `200` | `404` |

## Permiso por URL

| Paso | URL | Permiso |
| --- | --- | --- |
| 1 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchase-sequences` | `perm:purchase:purchase_sequences:create` |
| 2 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases` | `perm:purchase:purchases:create` |
| 3 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/confirmation` | `perm:purchase:purchases:update` |
| 4 | `GET /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases?status=CONFIRMED&number=CP-202611-000001` | `perm:purchase:purchases:read` |
| 5 | `GET /api/v1/companies/d14a0000-0000-4000-8000-000000000099/purchases/<COMPRA>` | `perm:purchase:purchases:read` |

## Ejemplos

- Puede: `operario.dao` (grupos `Compras`, `Ventas` e `Inventario`, permisos explícitos de `purchase`) registran, confirman y anulan compras de las sucursales asignadas; `admin.dao` (grupo `admin`, `perm:purchase:all:all`) también, y además ajusta la tasa de impuesto de una línea; `admin.sio` (grupo `superadmin`) por comodín.
- No puede: ninguna cuenta de servicio escribe compras (ni el propio `purchase-service`); el operario (`Compras`, `Ventas` e `Inventario`) no ajusta tasas de línea; sin asignación a la sucursal, ni el comodín permite escribir.
