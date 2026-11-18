# Usuarios del ejercicio 5

| Usuario | Paso 1 | Paso 2 | Paso 3 | Paso 4 | Paso 5 | Paso 6 | Paso 7 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `inventory-test-operator` | `201` | `403` (cuenta de servicio) | `403` (cuenta de servicio) | `403` (cuenta de servicio) | `403` (cuenta de servicio) | `403` (cuenta de servicio) | — (no consulta) |
| `admin.sio` | `403` | `—` | `—` | `—` | `—` | `—` | `200` |
| `admin.dao` | `403` | `—` | `—` | `—` | `—` | `—` | `200` |
| `operario.dao` | `403` | `201` | `201` | `422` | `201` | `403` | `200` |

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

- Puede: `admin.sio` (SuperAdmin), `admin.dao` (Admin) y el usuario de las tres áreas (`operario.dao`) consultan inventario de las empresas donde son miembros y registran ajustes y conteos en las sucursales asignadas; solo `admin.sio` y `admin.dao` configuran políticas.
- No puede: ningún usuario humano aplica ni revierte operaciones (ni siquiera `admin.sio`, que tiene el permiso por comodín); ninguna cuenta de servicio registra ajustes, conteos ni políticas; el operario (`Compras`, `Ventas` e `Inventario`) recibe `403` al configurar políticas.
