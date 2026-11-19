# Paso 13. Cancelar el segundo conteo

Ejercicio 6: Conteos físicos.

## Llamada

`POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-counts/<CONTEO_2>/cancel`

Ejecuta: `operario.dao`.

### Solicitud

```json
{
  "reason": "Conteo repetido por la venta intermedia",
  "version": 2
}
```

### Por qué

- Queda `CANCELLED` sin ajustes; sus detalles ya no se pueden modificar.

## Permiso

La URL exige `perm:inventory:counts:create`.

Además exige un **usuario humano** (una cuenta de servicio recibe `403` aunque tenga el permiso por comodín), miembro `ACTIVE` de la empresa y, en ajustes y conteos, que la sucursal y la empresa estén activas (lo resuelve Operational Context con el token del usuario; la asignación a la sucursal no limita). Los usuarios con el permiso no repiten la llamada en este ejercicio porque cambiaría su estado.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.sio` | Sí | `—` | tiene `perm:all:all:all`; no se repite (cambiaría el estado) |
| `admin.dao` | Sí | `—` | tiene `perm:inventory:counts:create`; no se repite (cambiaría el estado) |
| `operario.dao` | Sí | `200` | tiene `perm:inventory:counts:create` |

Respuesta sin permiso (`403`), que no revela el permiso exigido:

```json
{
  "type": "https://sio/errors/inventory/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-counts/<CONTEO_2>/cancel",
  "code": "INVENTORY.FORBIDDEN",
  "trace_id": "<asignado por Inventory>"
}
```

## Respuesta esperada

Estado `200`.

```json
{
  "id": "<CONTEO_2>",
  "company_id": "d44a0000-0000-4000-8000-000000000001",
  "branch_id": "d44b0000-0000-4000-8000-000000000001",
  "status": "CANCELLED",
  "started_by_user_id": "d44c0000-0000-4000-8000-000000000103",
  "started_at": "<asignado por Inventory>",
  "completed_by_user_id": null,
  "completed_at": null,
  "cancelled_by_user_id": "d44c0000-0000-4000-8000-000000000103",
  "cancelled_at": "<asignado por Inventory>",
  "cancel_reason": "Conteo repetido por la venta intermedia",
  "operation_id": null,
  "observations": null,
  "version": 3,
  "created_at": "<asignado por Inventory>",
  "created_by": "operario.dao",
  "updated_at": "<asignado por Inventory>",
  "updated_by": "operario.dao",
  "details": [
    {
      "id": "<asignado por Inventory>",
      "inventory_count_id": "<CONTEO_2>",
      "company_product_id": "d44d0000-0000-4000-8000-000000000001",
      "system_quantity_snapshot": "8.0000",
      "counted_quantity": "0.0000",
      "difference_quantity": "-8.0000",
      "unit_cost": null,
      "inventory_adjustment_id": null,
      "counted_by_user_id": "d44c0000-0000-4000-8000-000000000103",
      "counted_at": "<asignado por Inventory>"
    }
  ],
  "adjustments": []
}
```
