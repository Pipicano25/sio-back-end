# Usuarios del ejercicio 6

| Usuario | Paso 1 | Paso 2 | Paso 3 | Paso 4 | Paso 5 | Paso 6 | Paso 7 | Paso 8 | Paso 9 | Paso 10 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `admin.test` | `—` | `—` | `—` | `—` | `—` | `—` | `—` | `—` | `—` | `200` |
| `supervisor.test` | `—` | `—` | `—` | `—` | `—` | `—` | `—` | `—` | `—` | `200` |
| `compras.test` | `201` | `201` | `201` | `422` | `201` | `201` | `200` | `201` | `201` | `200` |
| `ventas.test` | `403` | `403` | `403` | `403` | `403` | `403` | `403` | `403` | `403` | `403` |
| `inventario.test` | `403` | `403` | `403` | `403` | `403` | `403` | `403` | `403` | `403` | `403` |
| `reportes.test` | `403` | `403` | `403` | `403` | `403` | `403` | `403` | `403` | `403` | `200` |
| `consulta.test` | `403` | `403` | `403` | `403` | `403` | `403` | `403` | `403` | `403` | `200` |

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
| 9 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/lifecycle-events` | `perm:purchase:purchase_lifecycle_events:create` |
| 10 | `GET /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/lifecycle-events` | `perm:purchase:purchase_lifecycle_events:read` |

## Ejemplos

- Puede: `compras.test` (grupo `compras`, `perm:purchase:all:all`) registra, confirma y anula compras de las sucursales asignadas; `admin.test` también, por comodín; `supervisor.test` registra y confirma, pero no anula (no tiene `delete`); `reportes.test` y `consulta.test` solo consultan.
- No puede: ninguna cuenta de servicio escribe compras (ni el propio `purchase-service`); `ventas.test` e `inventario.test` reciben `403`; sin asignación a la sucursal, ni el comodín permite escribir.
