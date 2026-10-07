# Usuarios del ejercicio 6

| Usuario | Paso 1 | Paso 2 | Paso 3 | Paso 4 | Paso 5 | Paso 6 | Paso 7 | Paso 8 | Paso 9 | Paso 10 | Paso 11 | Paso 12 | Paso 13 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `inventory-test-operator` | `201` | `403` (cuenta de servicio) | `403` (cuenta de servicio) | `403` (cuenta de servicio) | `403` (cuenta de servicio) | `403` (cuenta de servicio) | — (no consulta) | `403` (cuenta de servicio) | `403` (cuenta de servicio) | `403` (cuenta de servicio) | `201` | `403` (cuenta de servicio) | `403` (cuenta de servicio) |
| `admin.test` | `403` | `—` | `—` | `—` | `—` | `—` | `200` | `—` | `—` | `—` | `403` | `—` | `—` |
| `supervisor.test` | `403` | `—` | `—` | `—` | `—` | `—` | `200` | `—` | `—` | `—` | `403` | `—` | `—` |
| `compras.test` | `403` | `403` | `403` | `403` | `403` | `403` | `403` | `403` | `403` | `403` | `403` | `403` | `403` |
| `ventas.test` | `403` | `403` | `403` | `403` | `403` | `403` | `403` | `403` | `403` | `403` | `403` | `403` | `403` |
| `inventario.test` | `403` | `201` | `200` | `200` | `200` | `200` | `200` | `201` | `200` | `200` | `403` | `409` | `200` |
| `reportes.test` | `403` | `403` | `403` | `403` | `403` | `403` | `403` | `403` | `403` | `403` | `403` | `403` | `403` |
| `consulta.test` | `403` | `403` | `403` | `403` | `403` | `403` | `403` | `403` | `403` | `403` | `403` | `403` | `403` |

## Permiso por URL

| Paso | URL | Permiso |
| --- | --- | --- |
| 1 | `POST /api/v1/inventory-entries` | `perm:inventory:entries:create` |
| 2 | `POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-counts` | `perm:inventory:counts:create` |
| 3 | `POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-counts/<CONTEO>/start` | `perm:inventory:counts:create` |
| 4 | `PUT /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-counts/<CONTEO>/details/d44d0000-0000-4000-8000-000000000001` | `perm:inventory:counts:create` |
| 5 | `PUT /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-counts/<CONTEO>/details/d44d0000-0000-4000-8000-000000000002` | `perm:inventory:counts:create` |
| 6 | `POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-counts/<CONTEO>/complete` | `perm:inventory:counts:create` |
| 7 | `GET /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-counts/<CONTEO>` | `perm:inventory:counts:read` |
| 8 | `POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-counts` | `perm:inventory:counts:create` |
| 9 | `POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-counts/<CONTEO_2>/start` | `perm:inventory:counts:create` |
| 10 | `PUT /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-counts/<CONTEO_2>/details/d44d0000-0000-4000-8000-000000000001` | `perm:inventory:counts:create` |
| 11 | `POST /api/v1/inventory-outputs` | `perm:inventory:outputs:create` |
| 12 | `POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-counts/<CONTEO_2>/complete` | `perm:inventory:counts:create` |
| 13 | `POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-counts/<CONTEO_2>/cancel` | `perm:inventory:counts:create` |

## Ejemplos

- Puede: `inventario.test`, `admin.test` y `supervisor.test` consultan inventario de las empresas donde son miembros; `inventario.test` registra ajustes y conteos en las sucursales asignadas; `admin.test` y `supervisor.test` configuran políticas (comodín).
- No puede: ningún usuario humano aplica ni revierte operaciones (ni siquiera `admin.test`, que tiene el permiso por comodín); ninguna cuenta de servicio registra ajustes, conteos ni políticas; `compras.test`, `ventas.test`, `reportes.test` y `consulta.test` reciben `403`.
