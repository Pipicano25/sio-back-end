# Usuarios del ejercicio 3: Compras del período

## Paso 1: `GET /api/v1/companies/d23a0000-0000-4000-8000-000000000001/reports/purchases?date_from=2026-10-01&date_to=2026-10-15`

Permiso: `perm:business-reporting:purchases:read`.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.sio` | Sí | `200` | tiene `perm:all:all:all` y los permisos de lectura del propietario |
| `admin.dao` | Sí | `200` | tiene `perm:business-reporting:purchases:read` y los permisos de lectura del propietario |
| `operario.dao` | Sí | `200` | tiene `perm:business-reporting:purchases:read` y los permisos de lectura del propietario |

## Paso 2: `GET /api/v1/companies/d23a0000-0000-4000-8000-000000000001/reports/purchases?date_from=2026-10-01&date_to=2026-10-15&category=PENDING_RECEIPT`

Permiso: `perm:business-reporting:purchases:read`.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.sio` | Sí | `200` | tiene `perm:all:all:all` y los permisos de lectura del propietario |
| `admin.dao` | Sí | `200` | tiene `perm:business-reporting:purchases:read` y los permisos de lectura del propietario |
| `operario.dao` | Sí | `200` | tiene `perm:business-reporting:purchases:read` y los permisos de lectura del propietario |
