# Paso 8. Consultar las políticas de la sucursal

Ejercicio 8: Políticas de inventario.

## Llamada

`GET /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-policies?branch_id=d44b0000-0000-4000-8000-000000000001`

Ejecuta: `inventario.test`.

### Por qué

- La bodega consulta las políticas pero no las configura (solo administradores y supervisores).

## Permiso

La URL exige `perm:inventory:product-policies:read`.

Además, el usuario debe ser miembro `ACTIVE` de la empresa y tener `perm:operational-context:application_users:read` (lo exige Operational Context al resolver su acceso). No se exige asignación a la sucursal.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `200` | tiene `perm:all:all:all` |
| `supervisor.test` | Sí | `200` | tiene `perm:all:all:read` |
| `compras.test` | No | `403` | no tiene `perm:inventory:product-policies:read` |
| `ventas.test` | No | `403` | no tiene `perm:inventory:product-policies:read` |
| `inventario.test` | Sí | `200` | tiene `perm:inventory:product-policies:read` |
| `reportes.test` | No | `403` | no tiene `perm:inventory:product-policies:read` |
| `consulta.test` | No | `403` | no tiene `perm:inventory:product-policies:read` |

Respuesta sin permiso (`403`), que no revela el permiso exigido:

```json
{
  "type": "https://sio/errors/inventory/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-policies",
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
      "id": "<POLITICA>",
      "company_id": "d44a0000-0000-4000-8000-000000000001",
      "branch_id": "d44b0000-0000-4000-8000-000000000001",
      "company_product_id": "d44d0000-0000-4000-8000-000000000001",
      "minimum_stock": "5.0000",
      "target_stock": "20.0000",
      "service_level": "0.9500",
      "safety_stock_method": "BASIC",
      "calculation_window_days": 90,
      "replenishment_mode": "MANUAL",
      "auto_purchase_enabled": false,
      "is_active": false,
      "version": 2,
      "created_at": "<asignado por Inventory>",
      "created_by": "admin.test",
      "updated_at": "<asignado por Inventory>",
      "updated_by": "admin.test"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```
