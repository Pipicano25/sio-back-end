# Usuarios del ejercicio 1

| Usuario | Paso 1 | Paso 2 | Paso 3 |
| --- | --- | --- | --- |
| `admin.test` | `—` | `200` | `—` |
| `supervisor.test` | `—` | `200` | `—` |
| `compras.test` | `201` | `200` | `409` |
| `ventas.test` | `—` | `200` | `—` |
| `inventario.test` | `—` | `200` | `—` |

## Permiso por URL

| Paso | URL | Permiso |
| --- | --- | --- |
| 1 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchase-sequences` | `perm:purchase:purchase_sequences:create` |
| 2 | `GET /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchase-sequences` | `perm:purchase:purchase_sequences:read` |
| 3 | `POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchase-sequences` | `perm:purchase:purchase_sequences:create` |

## Ejemplos

- Puede: `compras.test`, `ventas.test` e `inventario.test` (grupo `empleado`, permisos explícitos de `purchase`) registran, confirman y anulan compras de las sucursales asignadas; `supervisor.test` (grupo `admin`, `perm:purchase:all:all`) también, y además ajusta la tasa de impuesto de una línea; `admin.test` (grupo `superadmin`) por comodín.
- No puede: ninguna cuenta de servicio escribe compras (ni el propio `purchase-service`); el grupo `empleado` no ajusta tasas de línea; sin asignación a la sucursal, ni el comodín permite escribir.
