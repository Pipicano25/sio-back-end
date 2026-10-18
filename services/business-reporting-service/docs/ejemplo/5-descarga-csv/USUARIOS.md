# Usuarios del ejercicio 5: Descarga en CSV

## Paso 1: `GET /api/v1/companies/d23a0000-0000-4000-8000-000000000001/reports/purchases?date_from=2026-10-01&date_to=2026-10-15&format=csv`

Permiso: `perm:business-reporting:purchases:read`.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `200` | tiene `perm:all:all:all` y los permisos de lectura del propietario |
| `supervisor.test` | Sí | `200` | tiene `perm:all:all:read` y los permisos de lectura del propietario |
| `compras.test` | Sí | `200` | tiene `perm:business-reporting:purchases:read` y los permisos de lectura del propietario |
| `ventas.test` | No | `403` | no tiene `perm:business-reporting:purchases:read` |
| `inventario.test` | No | `403` | no tiene `perm:business-reporting:purchases:read` |
| `reportes.test` | Sí | `200` | tiene `perm:business-reporting:purchases:read` y los permisos de lectura del propietario |
| `consulta.test` | No | `403` | no tiene `perm:business-reporting:purchases:read` |
