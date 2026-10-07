# Usuarios del ejercicio 8

| Usuario | Paso 1 | Paso 2 | Paso 3 | Paso 4 | Paso 5 | Paso 6 | Paso 7 | Paso 8 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `inventory-test-operator` | — (no consulta) | `403` (cuenta de servicio) | `403` (cuenta de servicio) | `403` (cuenta de servicio) | `403` (cuenta de servicio) | `403` (cuenta de servicio) | `403` (cuenta de servicio) | — (no consulta) |
| `admin.test` | `200` | `201` | `200` | `422` | `201` | `409` | `200` | `200` |
| `supervisor.test` | `200` | `—` | `—` | `—` | `—` | `—` | `—` | `200` |
| `compras.test` | `403` | `403` | `403` | `403` | `403` | `403` | `403` | `403` |
| `ventas.test` | `403` | `403` | `403` | `403` | `403` | `403` | `403` | `403` |
| `inventario.test` | `200` | `403` | `403` | `403` | `403` | `403` | `403` | `200` |
| `reportes.test` | `403` | `403` | `403` | `403` | `403` | `403` | `403` | `403` |
| `consulta.test` | `403` | `403` | `403` | `403` | `403` | `403` | `403` | `403` |

## Permiso por URL

| Paso | URL | Permiso |
| --- | --- | --- |
| 1 | `GET /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-policy` | `perm:inventory:company-policies:read` |
| 2 | `POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-policy` | `perm:inventory:company-policies:update` |
| 3 | `PUT /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-policy` | `perm:inventory:company-policies:update` |
| 4 | `PUT /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-policy` | `perm:inventory:company-policies:update` |
| 5 | `POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-policies` | `perm:inventory:product-policies:update` |
| 6 | `POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-policies` | `perm:inventory:product-policies:update` |
| 7 | `POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-policies/<POLITICA>/deactivate` | `perm:inventory:product-policies:update` |
| 8 | `GET /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-policies?branch_id=d44b0000-0000-4000-8000-000000000001` | `perm:inventory:product-policies:read` |

## Ejemplos

- Puede: `inventario.test`, `admin.test` y `supervisor.test` consultan inventario de las empresas donde son miembros; `inventario.test` registra ajustes y conteos en las sucursales asignadas; `admin.test` y `supervisor.test` configuran políticas (comodín).
- No puede: ningún usuario humano aplica ni revierte operaciones (ni siquiera `admin.test`, que tiene el permiso por comodín); ninguna cuenta de servicio registra ajustes, conteos ni políticas; `compras.test`, `ventas.test`, `reportes.test` y `consulta.test` reciben `403`.
