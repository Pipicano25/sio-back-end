# Paso 6. Kardex del arroz

Ejercicio 4: Consultas de stock y kardex.

## Llamada

`GET /api/v1/companies/d44a0000-0000-4000-8000-000000000001/branches/d44b0000-0000-4000-8000-000000000001/kardex/d44d0000-0000-4000-8000-000000000001`

Ejecuta: `inventario.test`.

### Por qué

- Orden cronológico por `balance_sequence`, con saldos anterior y nuevo encadenados.

## Permiso

La URL exige `perm:inventory:movements:read`.

Además, el usuario debe ser miembro `ACTIVE` de la empresa y tener `perm:operational-context:application_users:read` (lo exige Operational Context al resolver su acceso). No se exige asignación a la sucursal.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `200` | tiene `perm:all:all:all` |
| `supervisor.test` | Sí | `200` | tiene `perm:all:all:read` |
| `compras.test` | No | `403` | no tiene `perm:inventory:movements:read` |
| `ventas.test` | No | `403` | no tiene `perm:inventory:movements:read` |
| `inventario.test` | Sí | `200` | tiene `perm:inventory:movements:read` |
| `reportes.test` | No | `403` | no tiene `perm:inventory:movements:read` |
| `consulta.test` | No | `403` | no tiene `perm:inventory:movements:read` |

Respuesta sin permiso (`403`), que no revela el permiso exigido:

```json
{
  "type": "https://sio/errors/inventory/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/companies/d44a0000-0000-4000-8000-000000000001/branches/d44b0000-0000-4000-8000-000000000001/kardex/d44d0000-0000-4000-8000-000000000001",
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
      "operation_id": "<asignado por Inventory>",
      "line_index": 0,
      "origin_detail_id": "d44f0300-0000-4000-8000-000000000001",
      "company_product_id": "d44d0000-0000-4000-8000-000000000001",
      "movement_type": "PURCHASE_ENTRY",
      "quantity": "10.0000",
      "previous_balance": "0.0000",
      "new_balance": "10.0000",
      "balance_sequence": 1,
      "unit_cost": "2500.5000",
      "movement_value": "25005.00",
      "cost_known": true,
      "reversed_movement_id": null,
      "origin_type": "PURCHASE",
      "origin_id": "d44e0000-0000-4000-8000-000000000001",
      "application_user_id": "d44c0000-0000-4000-8000-000000000001",
      "correlation_id": "d44f0200-0000-4000-8000-000000000001",
      "reason": null,
      "created_at": "<asignado por Inventory>",
      "created_by": "7c9a3b2e-5d4f-4ea0-b183-2c33f4a5b6d7"
    },
    {
      "id": "<asignado por Inventory>",
      "operation_id": "<asignado por Inventory>",
      "line_index": 0,
      "origin_detail_id": "d44f0300-0000-4000-8000-000000000003",
      "company_product_id": "d44d0000-0000-4000-8000-000000000001",
      "movement_type": "SALE_OUTPUT",
      "quantity": "3.0000",
      "previous_balance": "10.0000",
      "new_balance": "7.0000",
      "balance_sequence": 2,
      "unit_cost": "2500.5000",
      "movement_value": "7501.50",
      "cost_known": true,
      "reversed_movement_id": null,
      "origin_type": "SALE",
      "origin_id": "d44e0000-0000-4000-8000-000000000002",
      "application_user_id": "d44c0000-0000-4000-8000-000000000001",
      "correlation_id": "d44f0200-0000-4000-8000-000000000002",
      "reason": null,
      "created_at": "<asignado por Inventory>",
      "created_by": "7c9a3b2e-5d4f-4ea0-b183-2c33f4a5b6d7"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 2,
  "total_pages": 1
}
```
