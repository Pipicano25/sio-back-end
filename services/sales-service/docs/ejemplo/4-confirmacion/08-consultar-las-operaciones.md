# Paso 8. Consultar las operaciones de la venta

Ejercicio 4: Confirmación: precio cambiado e idempotencia.

## Llamada

`GET /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/operations`

Ejecuta: `ventas.test`.

### Por qué

- La primera clave quedó sin operación (el rechazo fue previo); la segunda, `SUCCEEDED`.

## Permiso

La URL exige `perm:sales:sale_operations:read`.

Además, el usuario debe ser miembro `ACTIVE` de la empresa (Operational Context, con su token). No se exige asignación a la sucursal.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `200` | tiene `perm:all:all:all` |
| `supervisor.test` | Sí | `200` | tiene `perm:all:all:read` |
| `compras.test` | No | `403` | no tiene `perm:sales:sale_operations:read` |
| `ventas.test` | Sí | `200` | tiene `perm:sales:all:read` |
| `inventario.test` | No | `403` | no tiene `perm:sales:sale_operations:read` |
| `reportes.test` | Sí | `200` | tiene `perm:sales:sale_operations:read` |
| `consulta.test` | Sí | `200` | tiene `perm:sales:sale_operations:read` |

Respuesta sin permiso (`403`), que no revela el permiso exigido:

```json
{
  "type": "https://sio/errors/sales/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/operations",
  "code": "SALES.FORBIDDEN",
  "trace_id": "<asignado por el servicio>"
}
```

## Respuesta esperada

Estado `200`.

```json
[
  {
    "id": "<asignado por el servicio>",
    "sale_id": "<VENTA>",
    "operation_type": "CONFIRM",
    "status": "SUCCEEDED",
    "correlation_id": "<asignado por el servicio>",
    "error_code": null,
    "error_details": null,
    "inventory_operation_id": "<asignado por el servicio>",
    "started_at": "<asignado por el servicio>",
    "updated_at": "<asignado por el servicio>",
    "completed_at": "<asignado por el servicio>"
  }
]
```
