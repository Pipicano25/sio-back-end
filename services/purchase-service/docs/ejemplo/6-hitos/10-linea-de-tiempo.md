# Paso 10. Consultar la línea de tiempo

Ejercicio 6: Hitos logísticos.

## Llamada

`GET /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/lifecycle-events`

Ejecuta: `compras.test`.

### Por qué

- Los intervalos se calculan al leer; nunca se escriben en Commercial Relationship.

## Permiso

La URL exige `perm:purchase:purchase_lifecycle_events:read`.

Además, el usuario debe ser miembro `ACTIVE` de la empresa (Operational Context, con su token). No se exige asignación a la sucursal.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `200` | tiene `perm:all:all:all` |
| `supervisor.test` | Sí | `200` | tiene `perm:all:all:read` |
| `compras.test` | Sí | `200` | tiene `perm:purchase:all:all` |
| `ventas.test` | No | `403` | no tiene `perm:purchase:purchase_lifecycle_events:read` |
| `inventario.test` | No | `403` | no tiene `perm:purchase:purchase_lifecycle_events:read` |
| `reportes.test` | Sí | `200` | tiene `perm:purchase:purchase_lifecycle_events:read` |
| `consulta.test` | Sí | `200` | tiene `perm:purchase:purchase_lifecycle_events:read` |

Respuesta sin permiso (`403`), que no revela el permiso exigido:

```json
{
  "type": "https://sio/errors/purchase/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/lifecycle-events",
  "code": "PURCHASE.FORBIDDEN",
  "trace_id": "<asignado por el servicio>"
}
```

## Respuesta esperada

Estado `200`.

```json
{
  "items": [
    {
      "id": "<asignado por el servicio>",
      "purchase_id": "<COMPRA>",
      "event_type": "ORDERED",
      "occurred_at": "2026-11-01T14:00:00Z",
      "recorded_by_user_id": "d14f1000-0000-4000-8000-000000000003",
      "source": "USER",
      "notes": null,
      "created_at": "<asignado por el servicio>",
      "created_by": "compras.test",
      "is_current": true
    },
    {
      "id": "<asignado por el servicio>",
      "purchase_id": "<COMPRA>",
      "event_type": "SUPPLIER_DISPATCHED",
      "occurred_at": "2026-11-02T14:00:00Z",
      "recorded_by_user_id": "d14f1000-0000-4000-8000-000000000003",
      "source": "SUPPLIER",
      "notes": null,
      "created_at": "<asignado por el servicio>",
      "created_by": "compras.test",
      "is_current": true
    },
    {
      "id": "<asignado por el servicio>",
      "purchase_id": "<COMPRA>",
      "event_type": "ARRIVED",
      "occurred_at": "2026-11-03T14:00:00Z",
      "recorded_by_user_id": "d14f1000-0000-4000-8000-000000000003",
      "source": "USER",
      "notes": null,
      "created_at": "<asignado por el servicio>",
      "created_by": "compras.test",
      "is_current": true
    },
    {
      "id": "<asignado por el servicio>",
      "purchase_id": "<COMPRA>",
      "event_type": "RECEIVED",
      "occurred_at": "2026-11-03T16:00:00Z",
      "recorded_by_user_id": "d14f1000-0000-4000-8000-000000000003",
      "source": "USER",
      "notes": null,
      "created_at": "<asignado por el servicio>",
      "created_by": "compras.test",
      "is_current": true
    },
    {
      "id": "<asignado por el servicio>",
      "purchase_id": "<COMPRA>",
      "event_type": "AVAILABLE_FOR_SALE",
      "occurred_at": "2026-11-04T14:00:00Z",
      "recorded_by_user_id": "d14f1000-0000-4000-8000-000000000003",
      "source": "USER",
      "notes": null,
      "created_at": "<asignado por el servicio>",
      "created_by": "compras.test",
      "is_current": true
    }
  ],
  "current": {
    "ORDERED": "<asignado por el servicio>",
    "SUPPLIER_DISPATCHED": "<asignado por el servicio>",
    "ARRIVED": "<asignado por el servicio>",
    "RECEIVED": "<asignado por el servicio>",
    "AVAILABLE_FOR_SALE": "<asignado por el servicio>"
  },
  "intervals": [
    {
      "from": "ORDERED",
      "to": "SUPPLIER_DISPATCHED",
      "hours": "24.00"
    },
    {
      "from": "SUPPLIER_DISPATCHED",
      "to": "ARRIVED",
      "hours": "24.00"
    },
    {
      "from": "ARRIVED",
      "to": "RECEIVED",
      "hours": "2.00"
    },
    {
      "from": "RECEIVED",
      "to": "AVAILABLE_FOR_SALE",
      "hours": "22.00"
    }
  ],
  "total_lead_time_hours": "72.00"
}
```
