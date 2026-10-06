# Usuarios del ejercicio 4

| Usuario | Paso 1 | Paso 2 | Paso 3 | Paso 4 | Paso 5 | Paso 6 | Paso 7 | Paso 8 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `inventory-test-operator` | `201` | `201` | — (no consulta) | — (no consulta) | — (no consulta) | — (no consulta) | — (no consulta) | — (no consulta) |
| `admin.test` | `403` | `403` | `200` | `200` | `200` | `200` | `200` | `404` |
| `supervisor.test` | `403` | `403` | `200` | `200` | `200` | `200` | `200` | `404` |
| `compras.test` | `403` | `403` | `403` | `403` | `403` | `403` | `403` | `403` |
| `ventas.test` | `403` | `403` | `403` | `403` | `403` | `403` | `403` | `403` |
| `inventario.test` | `403` | `403` | `200` | `200` | `200` | `200` | `200` | `404` |
| `reportes.test` | `403` | `403` | `403` | `403` | `403` | `403` | `403` | `403` |
| `consulta.test` | `403` | `403` | `403` | `403` | `403` | `403` | `403` | `403` |

## Permiso por URL

| Paso | URL | Permiso |
| --- | --- | --- |
| 1 | `POST /api/v1/inventory-entries` | `perm:inventory:entries:create` |
| 2 | `POST /api/v1/inventory-outputs` | `perm:inventory:outputs:create` |
| 3 | `GET /api/v1/companies/d44a0000-0000-4000-8000-000000000001/branches/d44b0000-0000-4000-8000-000000000001/balances/d44d0000-0000-4000-8000-000000000001` | `perm:inventory:balances:read` |
| 4 | `GET /api/v1/companies/d44a0000-0000-4000-8000-000000000001/branches/d44b0000-0000-4000-8000-000000000001/balances?in_stock_only=true` | `perm:inventory:balances:read` |
| 5 | `POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/branches/d44b0000-0000-4000-8000-000000000001/balances/lookup` | `perm:inventory:balances:read` |
| 6 | `GET /api/v1/companies/d44a0000-0000-4000-8000-000000000001/branches/d44b0000-0000-4000-8000-000000000001/kardex/d44d0000-0000-4000-8000-000000000001` | `perm:inventory:movements:read` |
| 7 | `GET /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-operations/by-key/d44f0100-0000-4000-8000-000000000001` | `perm:inventory:movements:read` |
| 8 | `GET /api/v1/companies/d44a0000-0000-4000-8000-000000000099/branches/d44b0000-0000-4000-8000-000000000001/balances` | `perm:inventory:balances:read` |

## Ejemplos

- Puede: `inventario.test`, `admin.test` y `supervisor.test` consultan stock y kardex de las empresas donde son miembros.
- No puede: ningún usuario humano aplica ni revierte operaciones (ni siquiera `admin.test`, que tiene el permiso por comodín); `compras.test`, `ventas.test`, `reportes.test` y `consulta.test` reciben `403` en las consultas.
