# Paso 4. Valor del inventario de la sucursal

Ejercicio 7: Valoración FIFO.

## Llamada

`GET /api/v1/companies/d44a0000-0000-4000-8000-000000000001/branches/d44b0000-0000-4000-8000-000000000001/valuation`

Ejecuta: `inventario.test`.

### Por qué

- Quedan 3 a 1 300: 3 900. El valor se recalcula siempre desde las capas abiertas.

## Permiso

La URL exige `perm:inventory:valuation:read`.

Además, el usuario debe ser miembro `ACTIVE` de la empresa y tener `perm:operational-context:application_users:read` (lo exige Operational Context al resolver su acceso). No se exige asignación a la sucursal.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `200` | tiene `perm:all:all:all` |
| `supervisor.test` | Sí | `200` | tiene `perm:all:all:read` |
| `compras.test` | No | `403` | no tiene `perm:inventory:valuation:read` |
| `ventas.test` | No | `403` | no tiene `perm:inventory:valuation:read` |
| `inventario.test` | Sí | `200` | tiene `perm:inventory:valuation:read` |
| `reportes.test` | No | `403` | no tiene `perm:inventory:valuation:read` |
| `consulta.test` | No | `403` | no tiene `perm:inventory:valuation:read` |

Respuesta sin permiso (`403`), que no revela el permiso exigido:

```json
{
  "type": "https://sio/errors/inventory/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/companies/d44a0000-0000-4000-8000-000000000001/branches/d44b0000-0000-4000-8000-000000000001/valuation",
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
      "company_product_id": "d44d0000-0000-4000-8000-000000000001",
      "quantity": "3.0000",
      "inventory_value": "3900.00",
      "average_unit_cost": "1300.0000",
      "open_layers": 1,
      "has_unknown_cost": false
    }
  ],
  "total_value": "3900.00",
  "has_unknown_cost": false,
  "page": 1,
  "page_size": 20,
  "total_records": 1
}
```
