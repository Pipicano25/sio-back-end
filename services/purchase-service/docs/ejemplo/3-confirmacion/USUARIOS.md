# Usuarios del ejercicio 3

| Usuario | Paso 1 | Paso 2 | Paso 3 | Paso 4 | Paso 5 | Paso 6 | Paso 7 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `admin.test` | `—` | `—` | `—` | `—` | `—` | `—` | `200` |
| `supervisor.test` | `—` | `—` | `—` | `—` | `—` | `—` | `200` |
| `compras.test` | `201` | `201` | `200` | `503` | `200` | `200` | `200` |
| `ventas.test` | `—` | `—` | `—` | `—` | `—` | `—` | `200` |
| `inventario.test` | `—` | `—` | `—` | `—` | `—` | `—` | `200` |

## Permiso por URL

| Paso | URL | Permiso |
| --- | --- | --- |
| 1 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchase-sequences` | `perm:purchase:purchase_sequences:create` |
| 2 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases` | `perm:purchase:purchases:create` |
| 3 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/confirmation` | `perm:purchase:purchases:update` |
| 4 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/receipt` | `perm:purchase:purchases:update` |
| 5 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/receipt` | `perm:purchase:purchases:update` |
| 6 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/receipt` | `perm:purchase:purchases:update` |
| 7 | `GET /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/operations` | `perm:purchase:purchase_operations:read` |

## Ejemplos

- Puede: `compras.test`, `ventas.test` e `inventario.test` (grupo `empleado`, permisos explícitos de `purchase`) registran, confirman y anulan compras de las sucursales asignadas; `supervisor.test` (grupo `admin`, `perm:purchase:all:all`) también, y además ajusta la tasa de impuesto de una línea; `admin.test` (grupo `superadmin`) por comodín.
- No puede: ninguna cuenta de servicio escribe compras (ni el propio `purchase-service`); el grupo `empleado` no ajusta tasas de línea; sin asignación a la sucursal, ni el comodín permite escribir.
