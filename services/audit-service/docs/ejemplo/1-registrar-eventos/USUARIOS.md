# Usuarios del ejercicio 1

| Usuario | Paso 1 | Paso 2 | Paso 3 | Paso 4 | Paso 5 | Paso 6 | Paso 7 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `audit-test-emitter` | `201` | `200` | `409` | `201` | `200` | `422` | `422` |
| `admin.sio` | `403` | `403` | `403` | `403` | `403` | `403` | `403` |
| `admin.dao` | `403` | `403` | `403` | `403` | `403` | `403` | `403` |
| `operario.dao` | `403` | `403` | `403` | `403` | `403` | `403` | `403` |

## Permiso por URL

| Paso | URL | Permiso |
| --- | --- | --- |
| 1 | `POST /api/v1/audit-events` | `perm:audit:audit-events:create` |
| 2 | `POST /api/v1/audit-events` | `perm:audit:audit-events:create` |
| 3 | `POST /api/v1/audit-events` | `perm:audit:audit-events:create` |
| 4 | `POST /api/v1/audit-events` | `perm:audit:audit-events:create` |
| 5 | `POST /api/v1/audit-events/batch` | `perm:audit:audit-events:create` |
| 6 | `POST /api/v1/audit-events/batch` | `perm:audit:audit-events:create` |
| 7 | `POST /api/v1/audit-events` | `perm:audit:audit-events:create` |

## Ejemplos

- Puede: ver la respuesta esperada de cada paso.
- No puede: `operario.dao` recibe `403` en todas las llamadas (no tiene permisos de auditoría); en el registro, incluso `admin.sio` recibe `403` porque no es una cuenta de servicio.
