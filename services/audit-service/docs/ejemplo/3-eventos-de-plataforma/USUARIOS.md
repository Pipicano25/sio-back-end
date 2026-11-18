# Usuarios del ejercicio 3

| Usuario | Paso 1 | Paso 2 | Paso 3 | Paso 4 |
| --- | --- | --- | --- | --- |
| `audit-test-emitter` | `201` | — (no consulta) | — (no consulta) | — (no consulta) |
| `admin.sio` | `403` | `200` | `200` | `404` |
| `admin.dao` | `403` | `403` | `403` | `404` |
| `operario.dao` | `403` | `403` | `403` | `403` |

## Permiso por URL

| Paso | URL | Permiso |
| --- | --- | --- |
| 1 | `POST /api/v1/audit-events` | `perm:audit:audit-events:create` |
| 2 | `GET /api/v1/platform-audit-events` | `perm:audit:platform-events:read` |
| 3 | `GET /api/v1/platform-entity-history/GlobalProduct/b22e0000-0000-4000-8000-000000000030` | `perm:audit:platform-events:read` |
| 4 | `GET /api/v1/companies/a11d0000-0000-4000-8000-000000000001/audit-events/<AUDIT_ID_PLATAFORMA>` | `perm:audit:audit-events:read` |

## Ejemplos

- Puede: ver la respuesta esperada de cada paso.
- No puede: `operario.dao` recibe `403` en todas las llamadas (no tiene permisos de auditoría); en el registro, incluso `admin.sio` recibe `403` porque no es una cuenta de servicio.
