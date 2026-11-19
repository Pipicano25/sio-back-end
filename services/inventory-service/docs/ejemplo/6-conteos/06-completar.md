# Paso 6. Completar el conteo

Ejercicio 6: Conteos físicos.

## Llamada

`POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-counts/<CONTEO>/complete`

Ejecuta: `operario.dao`.

### Solicitud

```json
{
  "completion_key": "d44f0600-0000-4000-8000-000000000001",
  "version": 2
}
```

### Por qué

- Una sola operación `ADJUSTMENT` (origen `COUNT`) con una línea por diferencia distinta de 0, todo o nada; un ajuste por línea enlazado a su detalle.
- La misma `completion_key` repetida devuelve el mismo resultado.

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
  "instance": "/api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-counts/<CONTEO>/complete",
  "code": "INVENTORY.FORBIDDEN",
  "trace_id": "<asignado por Inventory>"
}
```

## Respuesta esperada

Estado `200`.

```json
{
  "id": "<CONTEO>",
  "company_id": "d44a0000-0000-4000-8000-000000000001",
  "branch_id": "d44b0000-0000-4000-8000-000000000001",
  "status": "COMPLETED",
  "started_by_user_id": "d44c0000-0000-4000-8000-000000000103",
  "started_at": "<asignado por Inventory>",
  "completed_by_user_id": "d44c0000-0000-4000-8000-000000000103",
  "completed_at": "<asignado por Inventory>",
  "cancelled_by_user_id": null,
  "cancelled_at": null,
  "cancel_reason": null,
  "operation_id": "<asignado por Inventory>",
  "observations": "Conteo mensual ficticio",
  "version": 3,
  "created_at": "<asignado por Inventory>",
  "created_by": "operario.dao",
  "updated_at": "<asignado por Inventory>",
  "updated_by": "operario.dao",
  "details": [
    {
      "id": "<asignado por Inventory>",
      "inventory_count_id": "<CONTEO>",
      "company_product_id": "d44d0000-0000-4000-8000-000000000001",
      "system_quantity_snapshot": "10.0000",
      "counted_quantity": "8.0000",
      "difference_quantity": "-2.0000",
      "unit_cost": null,
      "inventory_adjustment_id": "<asignado por Inventory>",
      "counted_by_user_id": "d44c0000-0000-4000-8000-000000000103",
      "counted_at": "<asignado por Inventory>"
    },
    {
      "id": "<asignado por Inventory>",
      "inventory_count_id": "<CONTEO>",
      "company_product_id": "d44d0000-0000-4000-8000-000000000002",
      "system_quantity_snapshot": "5.5000",
      "counted_quantity": "6.0000",
      "difference_quantity": "0.5000",
      "unit_cost": null,
      "inventory_adjustment_id": "<asignado por Inventory>",
      "counted_by_user_id": "d44c0000-0000-4000-8000-000000000103",
      "counted_at": "<asignado por Inventory>"
    }
  ],
  "adjustments": [
    {
      "id": "<asignado por Inventory>",
      "operation_id": "<asignado por Inventory>",
      "movement_id": "<asignado por Inventory>",
      "company_id": "d44a0000-0000-4000-8000-000000000001",
      "branch_id": "d44b0000-0000-4000-8000-000000000001",
      "company_product_id": "d44d0000-0000-4000-8000-000000000001",
      "adjustment_type": "NEGATIVE",
      "quantity": "2.0000",
      "reason": "Diferencia del conteo físico",
      "previous_balance": "10.0000",
      "new_balance": "8.0000",
      "unit_cost": "2500.5000",
      "adjustment_value": "5001.00",
      "inventory_count_id": "<CONTEO>",
      "application_user_id": "d44c0000-0000-4000-8000-000000000103",
      "created_at": "<asignado por Inventory>",
      "created_by": "operario.dao",
      "movement": {
        "id": "<asignado por Inventory>",
        "line_index": 0,
        "origin_detail_id": "<asignado por Inventory>",
        "company_product_id": "d44d0000-0000-4000-8000-000000000001",
        "movement_type": "NEGATIVE_ADJUSTMENT",
        "quantity": "2.0000",
        "previous_balance": "10.0000",
        "new_balance": "8.0000",
        "balance_sequence": 2,
        "unit_cost": "2500.5000",
        "movement_value": "5001.00",
        "cost_known": true,
        "reversed_movement_id": null
      }
    },
    {
      "id": "<asignado por Inventory>",
      "operation_id": "<asignado por Inventory>",
      "movement_id": "<asignado por Inventory>",
      "company_id": "d44a0000-0000-4000-8000-000000000001",
      "branch_id": "d44b0000-0000-4000-8000-000000000001",
      "company_product_id": "d44d0000-0000-4000-8000-000000000002",
      "adjustment_type": "POSITIVE",
      "quantity": "0.5000",
      "reason": "Diferencia del conteo físico",
      "previous_balance": "5.5000",
      "new_balance": "6.0000",
      "unit_cost": "9800.0000",
      "adjustment_value": "4900.00",
      "inventory_count_id": "<CONTEO>",
      "application_user_id": "d44c0000-0000-4000-8000-000000000103",
      "created_at": "<asignado por Inventory>",
      "created_by": "operario.dao",
      "movement": {
        "id": "<asignado por Inventory>",
        "line_index": 1,
        "origin_detail_id": "<asignado por Inventory>",
        "company_product_id": "d44d0000-0000-4000-8000-000000000002",
        "movement_type": "POSITIVE_ADJUSTMENT",
        "quantity": "0.5000",
        "previous_balance": "5.5000",
        "new_balance": "6.0000",
        "balance_sequence": 2,
        "unit_cost": "9800.0000",
        "movement_value": "4900.00",
        "cost_known": true,
        "reversed_movement_id": null
      }
    }
  ]
}
```
