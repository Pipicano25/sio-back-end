# Paso 7. Consultar el conteo completado

Ejercicio 6: Conteos físicos.

## Llamada

`GET /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-counts/<CONTEO>`

Ejecuta: `inventario.test`.

### Por qué

- Incluye los detalles y, por estar completado, sus ajustes.

## Permiso

La URL exige `perm:inventory:counts:read`.

Además, el usuario debe ser miembro `ACTIVE` de la empresa y tener `perm:operational-context:application_users:read` (lo exige Operational Context al resolver su acceso). No se exige asignación a la sucursal.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `200` | tiene `perm:all:all:all` |
| `supervisor.test` | Sí | `200` | tiene `perm:all:all:read` |
| `compras.test` | No | `403` | no tiene `perm:inventory:counts:read` |
| `ventas.test` | No | `403` | no tiene `perm:inventory:counts:read` |
| `inventario.test` | Sí | `200` | tiene `perm:inventory:counts:read` |
| `reportes.test` | No | `403` | no tiene `perm:inventory:counts:read` |
| `consulta.test` | No | `403` | no tiene `perm:inventory:counts:read` |

Respuesta sin permiso (`403`), que no revela el permiso exigido:

```json
{
  "type": "https://sio/errors/inventory/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-counts/<CONTEO>",
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
  "started_by_user_id": "d44c0000-0000-4000-8000-000000000105",
  "started_at": "<asignado por Inventory>",
  "completed_by_user_id": "d44c0000-0000-4000-8000-000000000105",
  "completed_at": "<asignado por Inventory>",
  "cancelled_by_user_id": null,
  "cancelled_at": null,
  "cancel_reason": null,
  "operation_id": "<asignado por Inventory>",
  "observations": "Conteo mensual ficticio",
  "version": 3,
  "created_at": "<asignado por Inventory>",
  "created_by": "inventario.test",
  "updated_at": "<asignado por Inventory>",
  "updated_by": "inventario.test",
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
      "counted_by_user_id": "d44c0000-0000-4000-8000-000000000105",
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
      "counted_by_user_id": "d44c0000-0000-4000-8000-000000000105",
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
      "application_user_id": "d44c0000-0000-4000-8000-000000000105",
      "created_at": "<asignado por Inventory>",
      "created_by": "inventario.test",
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
      "application_user_id": "d44c0000-0000-4000-8000-000000000105",
      "created_at": "<asignado por Inventory>",
      "created_by": "inventario.test",
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
