# Usuarios del ejercicio 4

| Usuario | Paso 1 | Paso 2 | Paso 3 | Paso 4 | Paso 5 | Paso 6 | Paso 7 | Paso 8 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `inventory-test-operator` | `201` | `201` | — (no consulta) | — (no consulta) | — (no consulta) | — (no consulta) | — (no consulta) | — (no consulta) |
| `admin.sio` | `403` | `403` | `200` | `200` | `200` | `200` | `200` | `404` |
| `admin.dao` | `403` | `403` | `200` | `200` | `200` | `200` | `200` | `404` |
| `operario.dao` | `403` | `403` | `200` | `200` | `200` | `200` | `200` | `404` |

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

- Puede: `admin.sio` (SuperAdmin), `admin.dao` (Admin) y el usuario de las tres áreas (`operario.dao`) consultan inventario de las empresas donde son miembros y registran ajustes y conteos en las sucursales asignadas; solo `admin.sio` y `admin.dao` configuran políticas.
- No puede: ningún usuario humano aplica ni revierte operaciones (ni siquiera `admin.sio`, que tiene el permiso por comodín); ninguna cuenta de servicio registra ajustes, conteos ni políticas; el operario (`Compras`, `Ventas` e `Inventario`) recibe `403` al configurar políticas.
