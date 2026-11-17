# Usuarios del ejercicio 4: Evolución de existencias de una sucursal

## Paso 1: `GET /api/v1/companies/d23a0000-0000-4000-8000-000000000001/branches/d23b0000-0000-4000-8000-000000000001/reports/stock-evolution?date_from=2026-10-01&date_to=2026-10-15`

Permiso: `perm:business-reporting:stock_evolution:read`.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `200` | tiene `perm:all:all:all` y los permisos de lectura del propietario |
| `supervisor.test` | Sí | `200` | tiene `perm:business-reporting:stock_evolution:read` y los permisos de lectura del propietario |
| `compras.test` | Sí | `200` | tiene `perm:business-reporting:stock_evolution:read` y los permisos de lectura del propietario |
| `ventas.test` | Sí | `200` | tiene `perm:business-reporting:stock_evolution:read` y los permisos de lectura del propietario |
| `inventario.test` | Sí | `200` | tiene `perm:business-reporting:stock_evolution:read` y los permisos de lectura del propietario |

## Paso 2: `GET /api/v1/companies/d23a0000-0000-4000-8000-000000000001/reports/stock-evolution?date_from=2026-10-01&date_to=2026-10-15`

Permiso: `perm:business-reporting:stock_evolution:read`.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `200` | tiene `perm:all:all:all` y los permisos de lectura del propietario |
| `supervisor.test` | Sí | `200` | tiene `perm:business-reporting:stock_evolution:read` y los permisos de lectura del propietario |
| `compras.test` | Sí | `200` | tiene `perm:business-reporting:stock_evolution:read` y los permisos de lectura del propietario |
| `ventas.test` | Sí | `200` | tiene `perm:business-reporting:stock_evolution:read` y los permisos de lectura del propietario |
| `inventario.test` | Sí | `200` | tiene `perm:business-reporting:stock_evolution:read` y los permisos de lectura del propietario |
