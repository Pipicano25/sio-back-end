# Paso 7. Consultar el ajuste con su movimiento

Ejercicio 5: Ajustes de inventario.

## Llamada

`GET /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-adjustments/<AJUSTE>`

Ejecuta: `inventario.test`.

### Por qué

- El ajuste es inmutable: se corrige con otro ajuste de sentido contrario.

## Permiso

La URL exige `perm:inventory:adjustments:read`.

Además, el usuario debe ser miembro `ACTIVE` de la empresa y tener `perm:operational-context:application_users:read` (lo exige Operational Context al resolver su acceso). No se exige asignación a la sucursal.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `200` | tiene `perm:all:all:all` |
| `supervisor.test` | Sí | `200` | tiene `perm:all:all:read` |
| `compras.test` | No | `403` | no tiene `perm:inventory:adjustments:read` |
| `ventas.test` | No | `403` | no tiene `perm:inventory:adjustments:read` |
| `inventario.test` | Sí | `200` | tiene `perm:inventory:adjustments:read` |
| `reportes.test` | No | `403` | no tiene `perm:inventory:adjustments:read` |
| `consulta.test` | No | `403` | no tiene `perm:inventory:adjustments:read` |

Respuesta sin permiso (`403`), que no revela el permiso exigido:

```json
{
  "type": "https://sio/errors/inventory/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-adjustments/<AJUSTE>",
  "code": "INVENTORY.FORBIDDEN",
  "trace_id": "<asignado por Inventory>"
}
```

## Respuesta esperada

Estado `200`.

```json
{
  "id": "<AJUSTE>",
  "operation_id": "<asignado por Inventory>",
  "movement_id": "<asignado por Inventory>",
  "company_id": "d44a0000-0000-4000-8000-000000000001",
  "branch_id": "d44b0000-0000-4000-8000-000000000001",
  "company_product_id": "d44d0000-0000-4000-8000-000000000001",
  "adjustment_type": "NEGATIVE",
  "quantity": "3.0000",
  "reason": "Producto dañado en bodega",
  "previous_balance": "10.0000",
  "new_balance": "7.0000",
  "unit_cost": "2500.5000",
  "adjustment_value": "7501.50",
  "inventory_count_id": null,
  "application_user_id": "d44c0000-0000-4000-8000-000000000105",
  "created_at": "<asignado por Inventory>",
  "created_by": "inventario.test",
  "movement": {
    "id": "<asignado por Inventory>",
    "line_index": 0,
    "origin_detail_id": "<AJUSTE>",
    "company_product_id": "d44d0000-0000-4000-8000-000000000001",
    "movement_type": "NEGATIVE_ADJUSTMENT",
    "quantity": "3.0000",
    "previous_balance": "10.0000",
    "new_balance": "7.0000",
    "balance_sequence": 2,
    "unit_cost": "2500.5000",
    "movement_value": "7501.50",
    "cost_known": true,
    "reversed_movement_id": null
  }
}
```
