# Usuarios del ejercicio 3

| Usuario | Paso 1 | Paso 2 | Paso 3 | Paso 4 | Paso 5 | Paso 6 | Paso 7 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `inventory-test-operator` | `201` | `201` | `409` | `201` | `409` | `404` | `201` |
| `admin.test` | `403` | `403` | `403` | `403` | `403` | `403` | `403` |
| `supervisor.test` | `403` | `403` | `403` | `403` | `403` | `403` | `403` |
| `compras.test` | `403` | `403` | `403` | `403` | `403` | `403` | `403` |
| `ventas.test` | `403` | `403` | `403` | `403` | `403` | `403` | `403` |
| `inventario.test` | `403` | `403` | `403` | `403` | `403` | `403` | `403` |
| `reportes.test` | `403` | `403` | `403` | `403` | `403` | `403` | `403` |
| `consulta.test` | `403` | `403` | `403` | `403` | `403` | `403` | `403` |

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

- Puede: `inventario.test`, `admin.test` y `supervisor.test` consultan inventario de las empresas donde son miembros; `inventario.test` registra ajustes y conteos en las sucursales asignadas; `admin.test` y `supervisor.test` configuran políticas (comodín).
- No puede: ningún usuario humano aplica ni revierte operaciones (ni siquiera `admin.test`, que tiene el permiso por comodín); ninguna cuenta de servicio registra ajustes, conteos ni políticas; `compras.test`, `ventas.test`, `reportes.test` y `consulta.test` reciben `403`.
