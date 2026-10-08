# Usuarios del ejercicio 1

| Usuario | Paso 1 | Paso 2 | Paso 3 |
| --- | --- | --- | --- |
| `admin.test` | `—` | `200` | `—` |
| `supervisor.test` | `—` | `200` | `—` |
| `compras.test` | `403` | `403` | `403` |
| `ventas.test` | `201` | `200` | `409` |
| `inventario.test` | `403` | `403` | `403` |
| `reportes.test` | `403` | `200` | `403` |
| `consulta.test` | `403` | `200` | `403` |

## Permiso por URL

| Paso | URL | Permiso |
| --- | --- | --- |
| 1 | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sale-sequences` | `perm:sales:sale_sequences:create` |
| 2 | `GET /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sale-sequences` | `perm:sales:sale_sequences:read` |
| 3 | `POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sale-sequences` | `perm:sales:sale_sequences:create` |

## Ejemplos

- Puede: `ventas.test` (grupo `ventas`, `perm:sales:all:create|read|update|delete`) registra, confirma y anula ventas de las sucursales asignadas, **sin** ver costo ni margen; `admin.test` también, por comodín, y ve la rentabilidad; `supervisor.test` registra y confirma, ve la rentabilidad, pero no anula (no tiene `delete`); `reportes.test` y `consulta.test` solo consultan, sin rentabilidad.
- No puede: ninguna cuenta de servicio escribe ventas (ni el propio `sales-service`); `compras.test` e `inventario.test` reciben `403`; sin asignación a la sucursal, ni el comodín permite escribir.
