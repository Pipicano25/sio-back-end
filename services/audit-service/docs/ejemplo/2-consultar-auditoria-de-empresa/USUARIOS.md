# Usuarios del ejercicio 2

| Usuario | Paso 1 | Paso 2 | Paso 3 | Paso 4 | Paso 5 | Paso 6 |
| --- | --- | --- | --- | --- | --- | --- |
| `audit-test-emitter` | `200` | — (no consulta) | — (no consulta) | — (no consulta) | — (no consulta) | — (no consulta) |
| `admin.test` | `403` | `200` | `200` | `200` | `200` | `404` |
| `supervisor.test` | `403` | `200` | `200` | `200` | `200` | `404` |
| `compras.test` | `403` | `403` | `403` | `403` | `403` | `403` |
| `ventas.test` | `403` | `403` | `403` | `403` | `403` | `403` |
| `inventario.test` | `403` | `403` | `403` | `403` | `403` | `403` |
| `reportes.test` | `403` | `403` | `403` | `403` | `403` | `403` |
| `consulta.test` | `403` | `403` | `403` | `403` | `403` | `403` |

## Permiso por URL

| Paso | URL | Permiso |
| --- | --- | --- |
| 1 | `POST /api/v1/audit-events/batch` | `perm:audit:audit-events:create` |
| 2 | `GET /api/v1/companies/a11d0000-0000-4000-8000-000000000001/audit-events` | `perm:audit:audit-events:read` |
| 3 | `GET /api/v1/companies/a11d0000-0000-4000-8000-000000000001/audit-events?result=FAILURE&entity_type=PriceListItem` | `perm:audit:audit-events:read` |
| 4 | `GET /api/v1/companies/a11d0000-0000-4000-8000-000000000001/audit-events/<AUDIT_ID_CREACION>` | `perm:audit:audit-events:read` |
| 5 | `GET /api/v1/companies/a11d0000-0000-4000-8000-000000000001/entity-history/PriceListItem/b22e0000-0000-4000-8000-000000000010` | `perm:audit:audit-events:read` |
| 6 | `GET /api/v1/companies/a11d0000-0000-4000-8000-000000000099/audit-events` | `perm:audit:audit-events:read` |

## Ejemplos

- Puede: ver la respuesta esperada de cada paso.
- No puede: `inventario.test` recibe `403` en todas las llamadas (no tiene permisos de auditoría); en el registro, incluso `admin.test` recibe `403` porque no es una cuenta de servicio.
