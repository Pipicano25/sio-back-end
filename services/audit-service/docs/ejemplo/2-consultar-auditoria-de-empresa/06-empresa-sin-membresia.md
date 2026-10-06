# Paso 6. Consultar una empresa donde no es miembro

Ejercicio 2: Consultar la auditoría de una empresa.

## Llamada

`GET /api/v1/companies/a11d0000-0000-4000-8000-000000000099/audit-events`

Ejecuta: `supervisor.test`.

### Por qué

- Fuera del alcance → `404`, sin revelar si la empresa tiene eventos.

## Permiso

La URL exige `perm:audit:audit-events:read`.

Además, el usuario debe ser miembro `ACTIVE` de la empresa y tener `perm:operational-context:application_users:read` (lo exige Operational Context al resolver su acceso; FR-037).

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `404` | tiene `perm:all:all:all` |
| `supervisor.test` | Sí | `404` | tiene `perm:all:all:read` |
| `compras.test` | No | `403` | no tiene `perm:audit:audit-events:read` |
| `ventas.test` | No | `403` | no tiene `perm:audit:audit-events:read` |
| `inventario.test` | No | `403` | no tiene `perm:audit:audit-events:read` |
| `reportes.test` | No | `403` | no tiene `perm:audit:audit-events:read` |
| `consulta.test` | No | `403` | no tiene `perm:audit:audit-events:read` |

Respuesta sin permiso (`403`), que no revela el permiso exigido:

```json
{
  "type": "https://sio/errors/audit/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/companies/a11d0000-0000-4000-8000-000000000099/audit-events",
  "code": "AUDIT.FORBIDDEN",
  "trace_id": "<asignado por Audit>"
}
```

## Respuesta esperada

Estado `404`.

```json
{
  "type": "https://sio/errors/audit/not-found",
  "title": "Recurso no encontrado",
  "status": 404,
  "detail": "El recurso solicitado no existe o no está disponible para su usuario.",
  "instance": "/api/v1/companies/a11d0000-0000-4000-8000-000000000099/audit-events",
  "code": "AUDIT.NOT_FOUND",
  "trace_id": "<asignado por Audit>"
}
```
