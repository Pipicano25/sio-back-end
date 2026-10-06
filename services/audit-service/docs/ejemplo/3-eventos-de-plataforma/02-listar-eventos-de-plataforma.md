# Paso 2. Listar los eventos de plataforma

Ejercicio 3: Eventos de plataforma (sin empresa).

## Llamada

`GET /api/v1/platform-audit-events`

Ejecuta: `supervisor.test`.

### Por qué

- Solo eventos con `company_id` nulo; no consulta Operational Context.

## Permiso

La URL exige `perm:audit:platform-events:read`.

No exige membresía: es el permiso independiente de los eventos de plataforma.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `200` | tiene `perm:all:all:all` |
| `supervisor.test` | Sí | `200` | tiene `perm:all:all:read` |
| `compras.test` | No | `403` | no tiene `perm:audit:platform-events:read` |
| `ventas.test` | No | `403` | no tiene `perm:audit:platform-events:read` |
| `inventario.test` | No | `403` | no tiene `perm:audit:platform-events:read` |
| `reportes.test` | No | `403` | no tiene `perm:audit:platform-events:read` |
| `consulta.test` | No | `403` | no tiene `perm:audit:platform-events:read` |

Respuesta sin permiso (`403`), que no revela el permiso exigido:

```json
{
  "type": "https://sio/errors/audit/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/platform-audit-events",
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
      "id": "<AUDIT_ID_PLATAFORMA>",
      "event_id": "c33f0000-0000-4000-8000-000000000021",
      "company_id": null,
      "branch_id": null,
      "application_user_id": null,
      "keycloak_user_id": "13fb7acf-dac0-4fba-ae39-6759c77c3f97",
      "username_snapshot": "admin.test",
      "action": "UPDATE",
      "entity_type": "GlobalProduct",
      "entity_id": "b22e0000-0000-4000-8000-000000000030",
      "previous_values": {
        "name": "Arroz 500 g (ficticio)"
      },
      "new_values": {
        "name": "Arroz blanco 500 g (ficticio)"
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
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```
