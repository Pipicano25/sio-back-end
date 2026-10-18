# Usuarios del ejercicio 2: Ventas por sucursal

## Paso 1: `GET /api/v1/companies/d23a0000-0000-4000-8000-000000000001/reports/sales-by-branch?date_from=2026-10-01&date_to=2026-10-15`

Permiso: `perm:business-reporting:sales_by_branch:read`.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `200` | tiene `perm:all:all:all` y los permisos de lectura del propietario |
| `supervisor.test` | Sí | `200` | tiene `perm:all:all:read` y los permisos de lectura del propietario |
| `compras.test` | No | `403` | no tiene `perm:business-reporting:sales_by_branch:read` |
| `ventas.test` | No | `403` | no tiene `perm:business-reporting:sales_by_branch:read` |
| `inventario.test` | No | `403` | no tiene `perm:business-reporting:sales_by_branch:read` |
| `reportes.test` | Sí | `200` | tiene `perm:business-reporting:sales_by_branch:read` y los permisos de lectura del propietario |
| `consulta.test` | No | `403` | no tiene `perm:business-reporting:sales_by_branch:read` |
