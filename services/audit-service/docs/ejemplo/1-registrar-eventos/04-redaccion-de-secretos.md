# Paso 4. Evento con un valor sensible

Ejercicio 1: Registrar eventos de auditoría.

## Llamada

`POST /api/v1/audit-events`

Ejecuta: `audit-test-emitter` (cuenta de servicio).

### Solicitud

```json
{
  "event_id": "c33f0000-0000-4000-8000-000000000002",
  "company_id": "a11d0000-0000-4000-8000-000000000001",
  "keycloak_user_id": "13fb7acf-dac0-4fba-ae39-6759c77c3f97",
  "username_snapshot": "admin.test",
  "action": "UPDATE",
  "entity_type": "CompanySupplier",
  "entity_id": "b22e0000-0000-4000-8000-000000000020",
  "previous_values": {
    "portal": {
      "user": "proveedor",
      "api_key": "valor-ficticio-1"
    }
  },
  "new_values": {
    "portal": {
      "user": "proveedor",
      "api_key": "valor-ficticio-2"
    }
  },
  "result": "SUCCESS",
  "occurred_at": "2026-09-15T14:00:00-05:00"
}
```

### Por qué

- `api_key` está en la política de redacción: su valor se guarda como `"***"`.
- Las rutas ocultadas quedan en `redacted_paths`; el evento no se rechaza.
- Normalmente el emisor ya lo ocultó antes de su outbox; Audit lo repite como defensa.

## Permiso

La URL exige `perm:audit:audit-events:create`.

Además exige que el token sea de una **cuenta de servicio**: un usuario humano recibe `403` aunque tenga el permiso por comodín. Solo puede ejecutarla `audit-test-emitter` (o el cliente técnico de un servicio emisor con el mismo permiso).

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | No | `403` | tiene `perm:all:all:all` por comodín, pero no es una cuenta de servicio |
| `supervisor.test` | No | `403` | tiene `perm:all:all:create` por comodín, pero no es una cuenta de servicio |
| `compras.test` | No | `403` | no tiene `perm:audit:audit-events:create` y no es una cuenta de servicio |
| `ventas.test` | No | `403` | no tiene `perm:audit:audit-events:create` y no es una cuenta de servicio |
| `inventario.test` | No | `403` | no tiene `perm:audit:audit-events:create` y no es una cuenta de servicio |
| `reportes.test` | No | `403` | no tiene `perm:audit:audit-events:create` y no es una cuenta de servicio |
| `consulta.test` | No | `403` | no tiene `perm:audit:audit-events:create` y no es una cuenta de servicio |

Respuesta sin permiso (`403`), que no revela el permiso exigido:

```json
{
  "type": "https://sio/errors/audit/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/audit-events",
  "code": "AUDIT.FORBIDDEN",
  "trace_id": "<asignado por Audit>"
}
```

## Respuesta esperada

Estado `201`.

```json
{
  "id": "<asignado por Audit>",
  "event_id": "c33f0000-0000-4000-8000-000000000002",
  "company_id": "a11d0000-0000-4000-8000-000000000001",
  "branch_id": null,
  "application_user_id": null,
  "keycloak_user_id": "13fb7acf-dac0-4fba-ae39-6759c77c3f97",
  "username_snapshot": "admin.test",
  "action": "UPDATE",
  "entity_type": "CompanySupplier",
  "entity_id": "b22e0000-0000-4000-8000-000000000020",
  "previous_values": {
    "portal": {
      "user": "proveedor",
      "api_key": "***"
    }
  },
  "new_values": {
    "portal": {
      "user": "proveedor",
      "api_key": "***"
    }
  },
  "redacted_paths": [
    "new_values.portal.api_key",
    "previous_values.portal.api_key"
  ],
  "result": "SUCCESS",
  "reason": null,
  "request_id": null,
  "correlation_id": null,
  "source_service": "audit-test-emitter",
  "occurred_at": "2026-09-15T19:00:00Z",
  "recorded_at": "<asignado por Audit>",
  "created_by": "sub-sa-audit-test-emitter"
}
```
