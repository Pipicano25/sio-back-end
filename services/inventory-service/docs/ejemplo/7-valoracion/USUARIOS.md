# Usuarios del ejercicio 7

| Usuario | Paso 1 | Paso 2 | Paso 3 | Paso 4 | Paso 5 | Paso 6 | Paso 7 | Paso 8 | Paso 9 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `inventory-test-operator` | `201` | `201` | `201` | — (no consulta) | — (no consulta) | — (no consulta) | `409` | `201` | `201` |
| `admin.test` | `403` | `403` | `403` | `200` | `200` | `200` | `403` | `403` | `403` |
| `supervisor.test` | `403` | `403` | `403` | `200` | `200` | `200` | `403` | `403` | `403` |
| `compras.test` | `403` | `403` | `403` | `403` | `403` | `403` | `403` | `403` | `403` |
| `ventas.test` | `403` | `403` | `403` | `403` | `403` | `403` | `403` | `403` | `403` |
| `inventario.test` | `403` | `403` | `403` | `200` | `200` | `200` | `403` | `403` | `403` |
| `reportes.test` | `403` | `403` | `403` | `403` | `403` | `403` | `403` | `403` | `403` |
| `consulta.test` | `403` | `403` | `403` | `403` | `403` | `403` | `403` | `403` | `403` |

## Permiso por URL

| Paso | URL | Permiso |
| --- | --- | --- |
| 1 | `POST /api/v1/inventory-entries` | `perm:inventory:entries:create` |
| 2 | `POST /api/v1/inventory-entries` | `perm:inventory:entries:create` |
| 3 | `POST /api/v1/inventory-outputs` | `perm:inventory:outputs:create` |
| 4 | `GET /api/v1/companies/d44a0000-0000-4000-8000-000000000001/branches/d44b0000-0000-4000-8000-000000000001/valuation` | `perm:inventory:valuation:read` |
| 5 | `GET /api/v1/companies/d44a0000-0000-4000-8000-000000000001/branches/d44b0000-0000-4000-8000-000000000001/valuation/d44d0000-0000-4000-8000-000000000001/layers?include_closed=true` | `perm:inventory:valuation:read` |
| 6 | `GET /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-movements/<MOV_SALIDA>/cost-consumptions` | `perm:inventory:valuation:read` |
| 7 | `POST /api/v1/inventory-entries/<OP_ENTRADA>/reversal` | `perm:inventory:entries:create` |
| 8 | `POST /api/v1/inventory-outputs/<OP_SALIDA>/reversal` | `perm:inventory:outputs:create` |
| 9 | `POST /api/v1/inventory-entries/<OP_ENTRADA>/reversal` | `perm:inventory:entries:create` |

## Ejemplos

- Puede: `inventario.test`, `admin.test` y `supervisor.test` consultan inventario de las empresas donde son miembros; `inventario.test` registra ajustes y conteos en las sucursales asignadas; `admin.test` y `supervisor.test` configuran políticas (comodín).
- No puede: ningún usuario humano aplica ni revierte operaciones (ni siquiera `admin.test`, que tiene el permiso por comodín); ninguna cuenta de servicio registra ajustes, conteos ni políticas; `compras.test`, `ventas.test`, `reportes.test` y `consulta.test` reciben `403`.
