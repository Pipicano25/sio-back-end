# Paso 5. El mismo ajuste con su costo

Ejercicio 5: Ajustes de inventario.

## Llamada

`POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-adjustments`

Ejecuta: `inventario.test`.

### Solicitud

```json
{
  "adjustment_key": "d44f0500-0000-4000-8000-000000000004",
  "branch_id": "d44b0000-0000-4000-8000-000000000001",
  "company_product_id": "d44d0000-0000-4000-8000-000000000002",
  "adjustment_type": "POSITIVE",
  "quantity": "4",
  "unit_cost": "9800",
  "reason": "Inventario inicial encontrado"
}
```

### Por qué

- Con `unit_cost` la capa se crea con ese costo.

## Permiso

La URL exige `perm:inventory:adjustments:create`.

Además exige un **usuario humano** (una cuenta de servicio recibe `403` aunque tenga el permiso por comodín), miembro `ACTIVE` de la empresa y, en ajustes y conteos, con asignación `ACTIVE` a la sucursal (lo resuelve Operational Context con el token del usuario). Los usuarios con el permiso no repiten la llamada en este ejercicio porque cambiaría su estado.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `—` | tiene `perm:all:all:all`; no se repite (cambiaría el estado) |
| `supervisor.test` | Sí | `—` | tiene `perm:all:all:create`; no se repite (cambiaría el estado) |
| `compras.test` | No | `403` | no tiene `perm:inventory:adjustments:create` |
| `ventas.test` | No | `403` | no tiene `perm:inventory:adjustments:create` |
| `inventario.test` | Sí | `201` | tiene `perm:inventory:adjustments:create` |
| `reportes.test` | No | `403` | no tiene `perm:inventory:adjustments:create` |
| `consulta.test` | No | `403` | no tiene `perm:inventory:adjustments:create` |

Respuesta sin permiso (`403`), que no revela el permiso exigido:

```json
{
  "type": "https://sio/errors/inventory/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-adjustments",
  "code": "INVENTORY.FORBIDDEN",
  "trace_id": "<asignado por Inventory>"
}
```

## Respuesta esperada

Estado `201`.

```json
{
  "id": "<asignado por Inventory>",
  "operation_id": "<asignado por Inventory>",
  "movement_id": "<asignado por Inventory>",
  "company_id": "d44a0000-0000-4000-8000-000000000001",
  "branch_id": "d44b0000-0000-4000-8000-000000000001",
  "company_product_id": "d44d0000-0000-4000-8000-000000000002",
  "adjustment_type": "POSITIVE",
  "quantity": "4.0000",
  "reason": "Inventario inicial encontrado",
  "previous_balance": "0.0000",
  "new_balance": "4.0000",
  "unit_cost": "9800.0000",
  "adjustment_value": "39200.00",
  "inventory_count_id": null,
  "application_user_id": "d44c0000-0000-4000-8000-000000000105",
  "created_at": "<asignado por Inventory>",
  "created_by": "inventario.test",
  "movement": {
    "id": "<asignado por Inventory>",
    "line_index": 0,
    "origin_detail_id": "<asignado por Inventory>",
    "company_product_id": "d44d0000-0000-4000-8000-000000000002",
    "movement_type": "POSITIVE_ADJUSTMENT",
    "quantity": "4.0000",
    "previous_balance": "0.0000",
    "new_balance": "4.0000",
    "balance_sequence": 1,
    "unit_cost": "9800.0000",
    "movement_value": "39200.00",
    "cost_known": true,
    "reversed_movement_id": null
  }
}
```
