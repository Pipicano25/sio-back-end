# Paso 6. Consumos que explican el costo de la salida

Ejercicio 7: Valoración FIFO.

## Llamada

`GET /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-movements/<MOV_SALIDA>/cost-consumptions`

Ejecuta: `inventario.test`.

### Por qué

- Un consumo `CONSUME` por capa tomada; la suma de `cost_amount` es el `movement_value`.

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
  "instance": "/api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-movements/<MOV_SALIDA>/cost-consumptions",
  "code": "INVENTORY.FORBIDDEN",
  "trace_id": "<asignado por Inventory>"
}
```

## Respuesta esperada

Estado `200`.

```json
{
  "movement_id": "<MOV_SALIDA>",
  "items": [
    {
      "id": "<asignado por Inventory>",
      "cost_layer_id": "<asignado por Inventory>",
      "consumption_type": "CONSUME",
      "quantity": "10.0000",
      "unit_cost": "1000.0000",
      "cost_amount": "10000.00",
      "cost_known": true,
      "restores_consumption_id": null
    },
    {
      "id": "<asignado por Inventory>",
      "cost_layer_id": "<asignado por Inventory>",
      "consumption_type": "CONSUME",
      "quantity": "2.0000",
      "unit_cost": "1300.0000",
      "cost_amount": "2600.00",
      "cost_known": true,
      "restores_consumption_id": null
    }
  ]
}
```
