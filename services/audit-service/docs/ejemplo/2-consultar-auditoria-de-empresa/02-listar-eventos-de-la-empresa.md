# Paso 2. Listar los eventos de la empresa

Ejercicio 2: Consultar la auditoría de una empresa.

## Llamada

`GET /api/v1/companies/a11d0000-0000-4000-8000-000000000001/audit-events`

Ejecuta: `supervisor.test`.

### Por qué

- Orden del más reciente al más antiguo; paginado (`page_size` máximo 100).
- Solo eventos de esta empresa; nunca eventos de plataforma.

## Permiso

La URL exige `perm:audit:audit-events:read`.

Además, el usuario debe ser miembro `ACTIVE` de la empresa y tener `perm:operational-context:application_users:read` (lo exige Operational Context al resolver su acceso; FR-037).

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `200` | tiene `perm:all:all:all` |
| `supervisor.test` | Sí | `200` | tiene `perm:all:all:read` |
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
  "instance": "/api/v1/companies/a11d0000-0000-4000-8000-000000000001/audit-events",
  "code": "AUDIT.FORBIDDEN",
  "trace_id": "<asignado por Audit>"
}
```

## Respuesta esperada

Estado `200`.

```json
{
  "items": [
    {
      "id": "<asignado por Audit>",
      "event_id": "c33f0000-0000-4000-8000-000000000013",
      "company_id": "a11d0000-0000-4000-8000-000000000001",
      "branch_id": null,
      "application_user_id": null,
      "keycloak_user_id": "13fb7acf-dac0-4fba-ae39-6759c77c3f97",
      "username_snapshot": "admin.test",
      "action": "CHANGE_PRICE",
      "entity_type": "PriceListItem",
      "entity_id": "b22e0000-0000-4000-8000-000000000010",
      "previous_values": {
        "unit_price": "2000.00"
      },
      "new_values": {
        "unit_price": "1900.00"
      },
      "redacted_paths": [],
      "result": "FAILURE",
      "reason": "El precio en vigencia no se puede modificar",
      "request_id": null,
      "correlation_id": null,
      "source_service": "audit-test-emitter",
      "occurred_at": "2026-09-16T13:30:00Z",
      "recorded_at": "<asignado por Audit>",
      "created_by": "sub-sa-audit-test-emitter"
    },
    {
      "id": "<asignado por Audit>",
      "event_id": "c33f0000-0000-4000-8000-000000000012",
      "company_id": "a11d0000-0000-4000-8000-000000000001",
      "branch_id": null,
      "application_user_id": null,
      "keycloak_user_id": "13fb7acf-dac0-4fba-ae39-6759c77c3f97",
      "username_snapshot": "admin.test",
      "action": "CHANGE_PRICE",
      "entity_type": "PriceListItem",
      "entity_id": "b22e0000-0000-4000-8000-000000000010",
      "previous_values": {
        "unit_price": "2000.00"
      },
      "new_values": {
        "unit_price": "2100.00"
      },
      "redacted_paths": [],
      "result": "SUCCESS",
      "reason": null,
      "request_id": null,
      "correlation_id": null,
      "source_service": "audit-test-emitter",
      "occurred_at": "2026-09-15T19:00:00Z",
      "recorded_at": "<asignado por Audit>",
      "created_by": "sub-sa-audit-test-emitter"
    },
    {
      "id": "<AUDIT_ID_CREACION>",
      "event_id": "c33f0000-0000-4000-8000-000000000011",
      "company_id": "a11d0000-0000-4000-8000-000000000001",
      "branch_id": null,
      "application_user_id": null,
      "keycloak_user_id": "13fb7acf-dac0-4fba-ae39-6759c77c3f97",
      "username_snapshot": "admin.test",
      "action": "CREATE",
      "entity_type": "PriceListItem",
      "entity_id": "b22e0000-0000-4000-8000-000000000010",
      "previous_values": null,
      "new_values": {
        "unit_price": "2000.00"
      },
      "redacted_paths": [],
      "result": "SUCCESS",
      "reason": null,
      "request_id": null,
      "correlation_id": null,
      "source_service": "audit-test-emitter",
      "occurred_at": "2026-09-10T14:00:00Z",
      "recorded_at": "<asignado por Audit>",
      "created_by": "sub-sa-audit-test-emitter"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 3,
  "total_pages": 1
}
```
