# Usuarios del ejercicio 5

| Usuario | Paso 1 | Paso 2 | Paso 3 | Paso 4 | Paso 5 | Paso 6 | Paso 7 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `inventory-test-operator` | `201` | `403` (cuenta de servicio) | `403` (cuenta de servicio) | `403` (cuenta de servicio) | `403` (cuenta de servicio) | `403` (cuenta de servicio) | — (no consulta) |
| `admin.test` | `403` | `—` | `—` | `—` | `—` | `—` | `200` |
| `supervisor.test` | `403` | `—` | `—` | `—` | `—` | `—` | `200` |
| `compras.test` | `403` | `403` | `403` | `403` | `403` | `403` | `403` |
| `ventas.test` | `403` | `403` | `403` | `403` | `403` | `403` | `403` |
| `inventario.test` | `403` | `201` | `201` | `422` | `201` | `403` | `200` |
| `reportes.test` | `403` | `403` | `403` | `403` | `403` | `403` | `403` |
| `consulta.test` | `403` | `403` | `403` | `403` | `403` | `403` | `403` |

## Permiso por URL

| Paso | URL | Permiso |
| --- | --- | --- |
| 1 | `POST /api/v1/inventory-entries` | `perm:inventory:entries:create` |
| 2 | `POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-adjustments` | `perm:inventory:adjustments:create` |
| 3 | `POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-adjustments` | `perm:inventory:adjustments:create` |
| 4 | `POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-adjustments` | `perm:inventory:adjustments:create` |
| 5 | `POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-adjustments` | `perm:inventory:adjustments:create` |
| 6 | `POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-adjustments` | `perm:inventory:adjustments:create` |
| 7 | `GET /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-adjustments/<AJUSTE>` | `perm:inventory:adjustments:read` |

## Ejemplos

- Puede: `inventario.test`, `admin.test` y `supervisor.test` consultan inventario de las empresas donde son miembros; `inventario.test` registra ajustes y conteos en las sucursales asignadas; `admin.test` y `supervisor.test` configuran políticas (comodín).
- No puede: ningún usuario humano aplica ni revierte operaciones (ni siquiera `admin.test`, que tiene el permiso por comodín); ninguna cuenta de servicio registra ajustes, conteos ni políticas; `compras.test`, `ventas.test`, `reportes.test` y `consulta.test` reciben `403`.
