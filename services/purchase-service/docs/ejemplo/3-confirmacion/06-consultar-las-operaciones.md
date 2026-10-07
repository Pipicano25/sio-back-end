# Paso 6. Consultar las operaciones de la compra

Ejercicio 3: Confirmación idempotente.

## Llamada

`GET /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/operations`

Ejecuta: `compras.test`.

### Por qué

- La clave de idempotencia nunca se expone; `inventory_operation_id` identifica la entrada.

## Permiso

La URL exige `perm:purchase:purchase_operations:read`.

Además, el usuario debe ser miembro `ACTIVE` de la empresa (Operational Context, con su token). No se exige asignación a la sucursal.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `200` | tiene `perm:all:all:all` |
| `supervisor.test` | Sí | `200` | tiene `perm:all:all:read` |
| `compras.test` | Sí | `200` | tiene `perm:purchase:all:all` |
| `ventas.test` | No | `403` | no tiene `perm:purchase:purchase_operations:read` |
| `inventario.test` | No | `403` | no tiene `perm:purchase:purchase_operations:read` |
| `reportes.test` | Sí | `200` | tiene `perm:purchase:purchase_operations:read` |
| `consulta.test` | Sí | `200` | tiene `perm:purchase:purchase_operations:read` |

Respuesta sin permiso (`403`), que no revela el permiso exigido:

```json
{
  "type": "https://sio/errors/purchase/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/operations",
  "code": "PURCHASE.FORBIDDEN",
  "trace_id": "<asignado por el servicio>"
}
```

## Respuesta esperada

Estado `200`.

```json
[
  {
    "id": "<asignado por el servicio>",
    "purchase_id": "<COMPRA>",
    "operation_type": "CONFIRM",
    "status": "SUCCEEDED",
    "correlation_id": "<asignado por el servicio>",
    "error_code": null,
    "error_details": null,
    "inventory_operation_id": "<ENTRADA>",
    "started_at": "<asignado por el servicio>",
    "updated_at": "<asignado por el servicio>",
    "completed_at": "<asignado por el servicio>"
  }
]
```
