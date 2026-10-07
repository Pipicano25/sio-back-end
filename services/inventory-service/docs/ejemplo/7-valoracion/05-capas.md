# Paso 5. Capas del arroz, incluidas las cerradas

Ejercicio 7: Valoración FIFO.

## Llamada

`GET /api/v1/companies/d44a0000-0000-4000-8000-000000000001/branches/d44b0000-0000-4000-8000-000000000001/valuation/d44d0000-0000-4000-8000-000000000001/layers?include_closed=true`

Ejecuta: `inventario.test`.

### Por qué

- En orden FIFO; la primera quedó cerrada (`remaining_quantity` 0).

## Permiso

La URL exige `perm:inventory:valuation:read`.

Además, el usuario debe ser miembro `ACTIVE` de la empresa y tener `perm:operational-context:application_users:read` (lo exige Operational Context al resolver su acceso). No se exige asignación a la sucursal.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `200` | tiene `perm:all:all:all` |
| `supervisor.test` | Sí | `200` | tiene `perm:all:all:read` |
| `compras.test` | No | `403` | no tiene `perm:inventory:valuation:read` |
| `ventas.test` | No | `403` | no tiene `perm:inventory:valuation:read` |
| `inventario.test` | Sí | `200` | tiene `perm:inventory:valuation:read` |
| `reportes.test` | No | `403` | no tiene `perm:inventory:valuation:read` |
| `consulta.test` | No | `403` | no tiene `perm:inventory:valuation:read` |

Respuesta sin permiso (`403`), que no revela el permiso exigido:

```json
{
  "type": "https://sio/errors/inventory/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/companies/d44a0000-0000-4000-8000-000000000001/branches/d44b0000-0000-4000-8000-000000000001/valuation/d44d0000-0000-4000-8000-000000000001/layers",
  "code": "INVENTORY.FORBIDDEN",
  "trace_id": "<asignado por Inventory>"
}
```

## Respuesta esperada

Estado `200`.

```json
{
  "items": [
    {
      "id": "<asignado por Inventory>",
      "layer_kind": "ENTRY",
      "origin_movement_id": "<asignado por Inventory>",
      "original_quantity": "10.0000",
      "remaining_quantity": "0.0000",
      "unit_cost": "1000.0000",
      "cost_known": true,
      "currency_code": "COP",
      "received_at": "<asignado por Inventory>",
      "status": "CLOSED"
    },
    {
      "id": "<asignado por Inventory>",
      "layer_kind": "ENTRY",
      "origin_movement_id": "<asignado por Inventory>",
      "original_quantity": "5.0000",
      "remaining_quantity": "3.0000",
      "unit_cost": "1300.0000",
      "cost_known": true,
      "currency_code": "COP",
      "received_at": "<asignado por Inventory>",
      "status": "OPEN"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 2
}
```
