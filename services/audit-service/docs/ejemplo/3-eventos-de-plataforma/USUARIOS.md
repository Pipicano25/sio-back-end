# Usuarios del ejercicio 3

| Usuario | Paso 1 | Paso 2 | Paso 3 | Paso 4 |
| --- | --- | --- | --- | --- |
| `audit-test-emitter` | `201` | — (no consulta) | — (no consulta) | — (no consulta) |
| `admin.test` | `403` | `200` | `200` | `404` |
| `supervisor.test` | `403` | `200` | `200` | `404` |
| `compras.test` | `403` | `403` | `403` | `403` |
| `ventas.test` | `403` | `403` | `403` | `403` |
| `inventario.test` | `403` | `403` | `403` | `403` |
| `reportes.test` | `403` | `403` | `403` | `403` |
| `consulta.test` | `403` | `403` | `403` | `403` |

## Permiso por URL

| Paso | URL | Permiso |
| --- | --- | --- |
| 1 | `POST /api/v1/audit-events` | `perm:audit:audit-events:create` |
| 2 | `GET /api/v1/platform-audit-events` | `perm:audit:platform-events:read` |
| 3 | `GET /api/v1/platform-entity-history/GlobalProduct/b22e0000-0000-4000-8000-000000000030` | `perm:audit:platform-events:read` |
| 4 | `GET /api/v1/companies/a11d0000-0000-4000-8000-000000000001/audit-events/<AUDIT_ID_PLATAFORMA>` | `perm:audit:audit-events:read` |

## Ejemplos

- Puede: ver la respuesta esperada de cada paso.
- No puede: `inventario.test` recibe `403` en todas las llamadas (no tiene permisos de auditoría); en el registro, incluso `admin.test` recibe `403` porque no es una cuenta de servicio.
