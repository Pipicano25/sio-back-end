# Paso 5. Registrar un lote de eventos

Ejercicio 1: Registrar eventos de auditoría.

## Llamada

`POST /api/v1/audit-events/batch`

Ejecuta: `audit-test-emitter` (cuenta de servicio).

### Solicitud

```json
{
  "events": [
    {
      "event_id": "c33f0000-0000-4000-8000-000000000001",
      "company_id": "a11d0000-0000-4000-8000-000000000001",
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
      "result": "SUCCESS",
      "occurred_at": "2026-09-15T14:00:00-05:00"
    },
    {
      "event_id": "c33f0000-0000-4000-8000-000000000003",
      "company_id": "a11d0000-0000-4000-8000-000000000001",
      "keycloak_user_id": "13fb7acf-dac0-4fba-ae39-6759c77c3f97",
      "username_snapshot": "admin.test",
      "action": "INACTIVATE",
      "entity_type": "PriceListItem",
      "entity_id": "b22e0000-0000-4000-8000-000000000010",
      "previous_values": {
        "status": "ACTIVE"
      },
      "new_values": {
        "status": "INACTIVE"
      },
      "result": "SUCCESS",
      "occurred_at": "2026-09-15T14:00:00-05:00"
    },
    {
      "event_id": "c33f0000-0000-4000-8000-000000000004",
      "company_id": "a11d0000-0000-4000-8000-000000000001",
      "keycloak_user_id": "13fb7acf-dac0-4fba-ae39-6759c77c3f97",
      "username_snapshot": "admin.test",
      "action": "UPDATE",
      "entity_type": "PriceListItem",
      "entity_id": "b22e0000-0000-4000-8000-000000000010",
      "previous_values": {
        "unit_price": "2000.00"
      },
      "result": "FAILURE",
      "occurred_at": "2026-09-15T14:00:00-05:00",
      "reason": "Versión desactualizada"
    }
  ]
}
```

### Por qué

- Lote de 1 a 100 eventos; la respuesta indica `CREATED` o `ALREADY_EXISTS` por evento.
- El primer evento ya existía (paso 1): cuenta como confirmado.
- `FAILURE` sin cambios de valores es válido; `reason` es opcional.

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
  "instance": "/api/v1/audit-events/batch",
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
      "index": 0,
      "event_id": "c33f0000-0000-4000-8000-000000000001",
      "id": "<AUDIT_ID_CAMBIO>",
      "outcome": "ALREADY_EXISTS"
    },
    {
      "index": 1,
      "event_id": "c33f0000-0000-4000-8000-000000000003",
      "id": "<asignado por Audit>",
      "outcome": "CREATED"
    },
    {
      "index": 2,
      "event_id": "c33f0000-0000-4000-8000-000000000004",
      "id": "<asignado por Audit>",
      "outcome": "CREATED"
    }
  ]
}
```
