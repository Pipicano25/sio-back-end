# Usuarios del ejercicio 1: Productos más vendidos

## Paso 1: `GET /api/v1/companies/d23a0000-0000-4000-8000-000000000001/reports/top-selling-products?date_from=2026-10-01&date_to=2026-10-15`

Permiso: `perm:business-reporting:top_selling_products:read`.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `200` | tiene `perm:all:all:all` y los permisos de lectura del propietario |
| `supervisor.test` | Sí | `200` | tiene `perm:all:all:read` y los permisos de lectura del propietario |
| `compras.test` | No | `403` | no tiene `perm:business-reporting:top_selling_products:read` |
| `ventas.test` | Sí | `200` | tiene `perm:business-reporting:top_selling_products:read` y los permisos de lectura del propietario |
| `inventario.test` | No | `403` | no tiene `perm:business-reporting:top_selling_products:read` |
| `reportes.test` | Sí | `200` | tiene `perm:business-reporting:top_selling_products:read` y los permisos de lectura del propietario |
| `consulta.test` | No | `403` | no tiene `perm:business-reporting:top_selling_products:read` |

## Paso 2: `GET /api/v1/companies/d23a0000-0000-4000-8000-000000000001/reports/top-selling-products?date_from=2026-10-01&date_to=2026-10-15&rank_by=amount&include_presentations=true&limit=2`

Permiso: `perm:business-reporting:top_selling_products:read`.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `200` | tiene `perm:all:all:all` y los permisos de lectura del propietario |
| `supervisor.test` | Sí | `200` | tiene `perm:all:all:read` y los permisos de lectura del propietario |
| `compras.test` | No | `403` | no tiene `perm:business-reporting:top_selling_products:read` |
| `ventas.test` | Sí | `200` | tiene `perm:business-reporting:top_selling_products:read` y los permisos de lectura del propietario |
| `inventario.test` | No | `403` | no tiene `perm:business-reporting:top_selling_products:read` |
| `reportes.test` | Sí | `200` | tiene `perm:business-reporting:top_selling_products:read` y los permisos de lectura del propietario |
| `consulta.test` | No | `403` | no tiene `perm:business-reporting:top_selling_products:read` |
