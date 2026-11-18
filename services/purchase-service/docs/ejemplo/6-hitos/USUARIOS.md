# Usuarios del ejercicio 6

| Usuario | Paso 1 | Paso 2 | Paso 3 | Paso 4 | Paso 5 | Paso 6 | Paso 7 | Paso 8 | Paso 9 | Paso 10 | Paso 11 | Paso 12 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `admin.sio` | `—` | `—` | `—` | `—` | `—` | `—` | `—` | `—` | `—` | `—` | `—` | `200` |
| `admin.dao` | `—` | `—` | `—` | `—` | `—` | `—` | `—` | `—` | `—` | `—` | `—` | `200` |
| `operario.dao` | `201` | `201` | `201` | `422` | `201` | `201` | `200` | `409` | `200` | `201` | `201` | `200` |

## Permiso por URL

| Paso | URL | Permiso |
| --- | --- | --- |
| 1 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchase-sequences` | `perm:purchase:purchase_sequences:create` |
| 2 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases` | `perm:purchase:purchases:create` |
| 3 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/lifecycle-events` | `perm:purchase:purchase_lifecycle_events:create` |
| 4 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/lifecycle-events` | `perm:purchase:purchase_lifecycle_events:create` |
| 5 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/lifecycle-events` | `perm:purchase:purchase_lifecycle_events:create` |
| 6 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/lifecycle-events` | `perm:purchase:purchase_lifecycle_events:create` |
| 7 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/confirmation` | `perm:purchase:purchases:update` |
| 8 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/lifecycle-events` | `perm:purchase:purchase_lifecycle_events:create` |
| 9 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/receipt` | `perm:purchase:purchases:update` |
| 10 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/lifecycle-events` | `perm:purchase:purchase_lifecycle_events:create` |
| 11 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/lifecycle-events` | `perm:purchase:purchase_lifecycle_events:create` |
| 12 | `GET /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/lifecycle-events` | `perm:purchase:purchase_lifecycle_events:read` |

## Ejemplos

- Puede: `operario.dao` (grupo `empleado`, permisos explícitos de `purchase`) registran, confirman y anulan compras de las sucursales asignadas; `admin.dao` (grupo `admin`, `perm:purchase:all:all`) también, y además ajusta la tasa de impuesto de una línea; `admin.sio` (grupo `superadmin`) por comodín.
- No puede: ninguna cuenta de servicio escribe compras (ni el propio `purchase-service`); el grupo `empleado` no ajusta tasas de línea; sin asignación a la sucursal, ni el comodín permite escribir.
