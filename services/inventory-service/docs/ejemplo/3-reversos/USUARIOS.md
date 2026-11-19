# Usuarios del ejercicio 3

| Usuario | Paso 1 | Paso 2 | Paso 3 | Paso 4 | Paso 5 | Paso 6 | Paso 7 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `inventory-test-operator` | `201` | `201` | `409` | `201` | `409` | `404` | `201` |
| `admin.sio` | `403` | `403` | `403` | `403` | `403` | `403` | `403` |
| `admin.dao` | `403` | `403` | `403` | `403` | `403` | `403` | `403` |
| `operario.dao` | `403` | `403` | `403` | `403` | `403` | `403` | `403` |

## Permiso por URL

| Paso | URL | Permiso |
| --- | --- | --- |
| 1 | `POST /api/v1/inventory-entries` | `perm:inventory:entries:create` |
| 2 | `POST /api/v1/inventory-outputs` | `perm:inventory:outputs:create` |
| 3 | `POST /api/v1/inventory-entries/<OP_ENTRADA>/reversal` | `perm:inventory:entries:create` |
| 4 | `POST /api/v1/inventory-outputs/<OP_SALIDA>/reversal` | `perm:inventory:outputs:create` |
| 5 | `POST /api/v1/inventory-outputs/<OP_SALIDA>/reversal` | `perm:inventory:outputs:create` |
| 6 | `POST /api/v1/inventory-entries/<OP_ENTRADA>/reversal` | `perm:inventory:entries:create` |
| 7 | `POST /api/v1/inventory-entries/<OP_ENTRADA>/reversal` | `perm:inventory:entries:create` |

## Ejemplos

- Puede: `admin.sio` (SuperAdmin), `admin.dao` (Admin) y el usuario de las tres áreas (`operario.dao`) consultan inventario de las empresas donde son miembros y registran ajustes y conteos en sus sucursales activas; solo `admin.sio` y `admin.dao` configuran políticas.
- No puede: ningún usuario humano aplica ni revierte operaciones (ni siquiera `admin.sio`, que tiene el permiso por comodín); ninguna cuenta de servicio registra ajustes, conteos ni políticas; el operario (`Compras`, `Ventas` e `Inventario`) recibe `403` al configurar políticas.
