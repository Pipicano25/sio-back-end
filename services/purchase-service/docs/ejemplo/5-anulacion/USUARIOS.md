# Usuarios del ejercicio 5

| Usuario | Paso 1 | Paso 2 | Paso 3 | Paso 4 | Paso 5 | Paso 6 | Paso 7 | Paso 8 | Paso 9 | Paso 10 | Paso 11 | Paso 12 | Paso 13 | Paso 14 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `admin.sio` | `—` | `—` | `—` | `—` | `—` | `—` | `—` | `—` | `—` | `—` | `—` | `—` | `—` | `—` |
| `admin.dao` | `—` | `—` | `—` | `—` | `—` | `—` | `—` | `—` | `—` | `—` | `—` | `—` | `—` | `—` |
| `operario.dao` | `201` | `201` | `200` | `201` | `200` | `200` | `201` | `200` | `200` | `200` | `201` | `200` | `200` | `409` |

## Permiso por URL

| Paso | URL | Permiso |
| --- | --- | --- |
| 1 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchase-sequences` | `perm:purchase:purchase_sequences:create` |
| 2 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases` | `perm:purchase:purchases:create` |
| 3 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<BORRADOR>/cancellation` | `perm:purchase:purchases:delete` |
| 4 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases` | `perm:purchase:purchases:create` |
| 5 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<PENDIENTE>/confirmation` | `perm:purchase:purchases:update` |
| 6 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<PENDIENTE>/cancellation` | `perm:purchase:purchases:delete` |
| 7 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases` | `perm:purchase:purchases:create` |
| 8 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/confirmation` | `perm:purchase:purchases:update` |
| 9 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/receipt` | `perm:purchase:purchases:update` |
| 10 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/cancellation` | `perm:purchase:purchases:delete` |
| 11 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases` | `perm:purchase:purchases:create` |
| 12 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<VENDIDA>/confirmation` | `perm:purchase:purchases:update` |
| 13 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<VENDIDA>/receipt` | `perm:purchase:purchases:update` |
| 14 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<VENDIDA>/cancellation` | `perm:purchase:purchases:delete` |

## Ejemplos

- Puede: `operario.dao` (grupo `empleado`, permisos explícitos de `purchase`) registran, confirman y anulan compras de las sucursales asignadas; `admin.dao` (grupo `admin`, `perm:purchase:all:all`) también, y además ajusta la tasa de impuesto de una línea; `admin.sio` (grupo `superadmin`) por comodín.
- No puede: ninguna cuenta de servicio escribe compras (ni el propio `purchase-service`); el grupo `empleado` no ajusta tasas de línea; sin asignación a la sucursal, ni el comodín permite escribir.
