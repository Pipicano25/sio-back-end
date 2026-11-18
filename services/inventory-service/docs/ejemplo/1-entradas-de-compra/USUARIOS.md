# Usuarios del ejercicio 1

| Usuario | Paso 1 | Paso 2 | Paso 3 | Paso 4 |
| --- | --- | --- | --- | --- |
| `inventory-test-operator` | `201` | `200` | `409` | `422` |
| `admin.sio` | `403` | `403` | `403` | `403` |
| `admin.dao` | `403` | `403` | `403` | `403` |
| `operario.dao` | `403` | `403` | `403` | `403` |

## Permiso por URL

| Paso | URL | Permiso |
| --- | --- | --- |
| 1 | `POST /api/v1/inventory-entries` | `perm:inventory:entries:create` |
| 2 | `POST /api/v1/inventory-entries` | `perm:inventory:entries:create` |
| 3 | `POST /api/v1/inventory-entries` | `perm:inventory:entries:create` |
| 4 | `POST /api/v1/inventory-entries` | `perm:inventory:entries:create` |

## Ejemplos

- Puede: `admin.sio` (SuperAdmin), `admin.dao` (Admin) y el usuario del grupo `empleado` (`operario.dao`) consultan inventario de las empresas donde son miembros y registran ajustes y conteos en las sucursales asignadas; solo `admin.sio` y `admin.dao` configuran políticas.
- No puede: ningún usuario humano aplica ni revierte operaciones (ni siquiera `admin.sio`, que tiene el permiso por comodín); ninguna cuenta de servicio registra ajustes, conteos ni políticas; el grupo `empleado` recibe `403` al configurar políticas.
