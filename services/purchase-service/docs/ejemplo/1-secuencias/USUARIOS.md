# Usuarios del ejercicio 1

| Usuario | Paso 1 | Paso 2 | Paso 3 |
| --- | --- | --- | --- |
| `admin.test` | `—` | `200` | `—` |
| `supervisor.test` | `—` | `200` | `—` |
| `compras.test` | `201` | `200` | `409` |
| `ventas.test` | `403` | `403` | `403` |
| `inventario.test` | `403` | `403` | `403` |
| `reportes.test` | `403` | `200` | `403` |
| `consulta.test` | `403` | `200` | `403` |

## Permiso por URL

| Paso | URL | Permiso |
| --- | --- | --- |
| 1 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchase-sequences` | `perm:purchase:purchase_sequences:create` |
| 2 | `GET /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchase-sequences` | `perm:purchase:purchase_sequences:read` |
| 3 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchase-sequences` | `perm:purchase:purchase_sequences:create` |

## Ejemplos

- Puede: `compras.test` (grupo `compras`, `perm:purchase:all:all`) registra, confirma y anula compras de las sucursales asignadas; `admin.test` también, por comodín; `supervisor.test` registra y confirma, pero no anula (no tiene `delete`); `reportes.test` y `consulta.test` solo consultan.
- No puede: ninguna cuenta de servicio escribe compras (ni el propio `purchase-service`); `ventas.test` e `inventario.test` reciben `403`; sin asignación a la sucursal, ni el comodín permite escribir.
