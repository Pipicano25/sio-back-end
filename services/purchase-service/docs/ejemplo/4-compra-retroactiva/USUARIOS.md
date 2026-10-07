# Usuarios del ejercicio 4

| Usuario | Paso 1 | Paso 2 | Paso 3 | Paso 4 | Paso 5 |
| --- | --- | --- | --- | --- | --- |
| `admin.test` | `—` | `—` | `—` | `—` | `—` |
| `supervisor.test` | `—` | `—` | `—` | `—` | `—` |
| `compras.test` | `201` | `201` | `200` | `201` | `200` |
| `ventas.test` | `403` | `403` | `403` | `403` | `403` |
| `inventario.test` | `403` | `403` | `403` | `403` | `403` |
| `reportes.test` | `403` | `403` | `403` | `403` | `403` |
| `consulta.test` | `403` | `403` | `403` | `403` | `403` |

## Permiso por URL

| Paso | URL | Permiso |
| --- | --- | --- |
| 1 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchase-sequences` | `perm:purchase:purchase_sequences:create` |
| 2 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases` | `perm:purchase:purchases:create` |
| 3 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<NOVIEMBRE>/confirmation` | `perm:purchase:purchases:update` |
| 4 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases` | `perm:purchase:purchases:create` |
| 5 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<OCTUBRE>/confirmation` | `perm:purchase:purchases:update` |

## Ejemplos

- Puede: `compras.test` (grupo `compras`, `perm:purchase:all:all`) registra, confirma y anula compras de las sucursales asignadas; `admin.test` también, por comodín; `supervisor.test` registra y confirma, pero no anula (no tiene `delete`); `reportes.test` y `consulta.test` solo consultan.
- No puede: ninguna cuenta de servicio escribe compras (ni el propio `purchase-service`); `ventas.test` e `inventario.test` reciben `403`; sin asignación a la sucursal, ni el comodín permite escribir.
