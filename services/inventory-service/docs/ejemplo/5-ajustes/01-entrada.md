# Paso 1. Entrada de 10 unidades de arroz a 2 500,50

Ejercicio 5: Ajustes de inventario.

## Llamada

`POST /api/v1/inventory-entries`

Ejecuta: `inventory-test-operator` (cuenta de servicio).

### Solicitud

```json
{
  "operation_key": "d44f0100-0000-4000-8000-000000000001",
  "company_id": "d44a0000-0000-4000-8000-000000000001",
  "branch_id": "d44b0000-0000-4000-8000-000000000001",
  "origin_type": "PURCHASE",
  "origin_id": "d44e0000-0000-4000-8000-000000000001",
  "application_user_id": "d44c0000-0000-4000-8000-000000000001",
  "correlation_id": "d44f0200-0000-4000-8000-000000000001",
  "reason": null,
  "lines": [
    {
      "origin_detail_id": "d44f0300-0000-4000-8000-000000000001",
      "company_product_id": "d44d0000-0000-4000-8000-000000000001",
      "quantity": "10",
      "unit_cost": "2500.50"
    }
  ]
}
```

### Por qué

- Crea el saldo y una capa FIFO de 10 a 2 500,50.

## Permiso

La URL exige `perm:inventory:entries:create`.

Además exige que el token sea de una **cuenta de servicio**: un usuario humano recibe `403` aunque tenga el permiso por comodín. Solo puede ejecutarla `inventory-test-operator` (o el cliente técnico de Purchase o Sales con el mismo permiso).

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | No | `403` | tiene `perm:all:all:all` por comodín, pero no es una cuenta de servicio |
| `supervisor.test` | No | `403` | tiene `perm:all:all:create` por comodín, pero no es una cuenta de servicio |
| `compras.test` | No | `403` | no tiene `perm:inventory:entries:create` y no es una cuenta de servicio |
| `ventas.test` | No | `403` | no tiene `perm:inventory:entries:create` y no es una cuenta de servicio |
| `inventario.test` | No | `403` | no tiene `perm:inventory:entries:create` y no es una cuenta de servicio |
| `reportes.test` | No | `403` | no tiene `perm:inventory:entries:create` y no es una cuenta de servicio |
| `consulta.test` | No | `403` | no tiene `perm:inventory:entries:create` y no es una cuenta de servicio |

Respuesta sin permiso (`403`), que no revela el permiso exigido:

```json
{
  "type": "https://sio/errors/inventory/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/inventory-entries",
  "code": "INVENTORY.FORBIDDEN",
  "trace_id": "<asignado por Inventory>"
}
```

## Respuesta esperada

Estado `201`.

```json
{
  "id": "<asignado por Inventory>",
  "operation_key": "d44f0100-0000-4000-8000-000000000001",
  "operation_type": "ENTRY",
  "company_id": "d44a0000-0000-4000-8000-000000000001",
  "branch_id": "d44b0000-0000-4000-8000-000000000001",
  "origin_type": "PURCHASE",
  "origin_id": "d44e0000-0000-4000-8000-000000000001",
  "application_user_id": "d44c0000-0000-4000-8000-000000000001",
  "correlation_id": "d44f0200-0000-4000-8000-000000000001",
  "reason": null,
  "reverses_operation_id": null,
  "reversed_by_operation_id": null,
  "created_at": "<asignado por Inventory>",
  "created_by": "7c9a3b2e-5d4f-4ea0-b183-2c33f4a5b6d7",
  "movements": [
    {
      "id": "<asignado por Inventory>",
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
      "reversed_movement_id": null
    }
  ],
  "balances": [
    {
      "company_product_id": "d44d0000-0000-4000-8000-000000000001",
      "quantity": "10.0000",
      "inventory_value": "25005.00",
      "average_unit_cost": "2500.5000",
      "has_unknown_cost": false
    }
  ]
}
```
