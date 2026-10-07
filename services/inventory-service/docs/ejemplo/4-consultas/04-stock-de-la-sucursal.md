# Paso 4. Stock de la sucursal (solo con existencias)

Ejercicio 4: Consultas de stock y kardex.

## Llamada

`GET /api/v1/companies/d44a0000-0000-4000-8000-000000000001/branches/d44b0000-0000-4000-8000-000000000001/balances?in_stock_only=true`

Ejecuta: `inventario.test`.

### Por qué

- Paginado (`page_size` 20 por defecto, máximo 100) y ordenado por producto.

## Permiso

La URL exige `perm:inventory:balances:read`.

Además, el usuario debe ser miembro `ACTIVE` de la empresa y tener `perm:operational-context:application_users:read` (lo exige Operational Context al resolver su acceso). No se exige asignación a la sucursal.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `200` | tiene `perm:all:all:all` |
| `supervisor.test` | Sí | `200` | tiene `perm:all:all:read` |
| `compras.test` | No | `403` | no tiene `perm:inventory:balances:read` |
| `ventas.test` | No | `403` | no tiene `perm:inventory:balances:read` |
| `inventario.test` | Sí | `200` | tiene `perm:inventory:balances:read` |
| `reportes.test` | No | `403` | no tiene `perm:inventory:balances:read` |
| `consulta.test` | No | `403` | no tiene `perm:inventory:balances:read` |

Respuesta sin permiso (`403`), que no revela el permiso exigido:

```json
{
  "type": "https://sio/errors/inventory/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/companies/d44a0000-0000-4000-8000-000000000001/branches/d44b0000-0000-4000-8000-000000000001/balances",
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
      "company_id": "d44a0000-0000-4000-8000-000000000001",
      "branch_id": "d44b0000-0000-4000-8000-000000000001",
      "company_product_id": "d44d0000-0000-4000-8000-000000000001",
      "quantity": "7.0000",
      "last_movement_at": "<asignado por Inventory>",
      "balance_sequence": 2,
      "inventory_value": "17503.50",
      "average_unit_cost": "2500.5000",
      "has_unknown_cost": false
    },
    {
      "company_id": "d44a0000-0000-4000-8000-000000000001",
      "branch_id": "d44b0000-0000-4000-8000-000000000001",
      "company_product_id": "d44d0000-0000-4000-8000-000000000002",
      "quantity": "5.5000",
      "last_movement_at": "<asignado por Inventory>",
      "balance_sequence": 1,
      "inventory_value": "53900.00",
      "average_unit_cost": "9800.0000",
      "has_unknown_cost": false
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 2,
  "total_pages": 1
}
```
