# Paso 2. Bajo mínimo en una sucursal

Ejercicio 4: Productos bajo el mínimo.

## Llamada

`GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/low-stock-products?branch_id=d22b0000-0000-4000-8000-000000000002`

Ejecuta: `inventario.test`.

### Por qué

- Solo los pares de NORTE.

## Permiso

La URL exige `perm:product-inventory-query:low_stock_products:read`.

Además exige `perm:product-inventory-query:stock:read`, `perm:inventory:product-policies:read`.

Además, el usuario debe ser miembro `ACTIVE` de la empresa (lo verifica Operational Context con su token antes de cualquier otra consulta). No se exige asignación a la sucursal.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `200` | tiene `perm:all:all:all`, `perm:all:all:all`, `perm:all:all:all` |
| `supervisor.test` | Sí | `200` | tiene `perm:all:all:read`, `perm:all:all:read`, `perm:all:all:read` |
| `compras.test` | No | `403` | no tiene `perm:product-inventory-query:low_stock_products:read` |
| `ventas.test` | No | `403` | no tiene `perm:product-inventory-query:low_stock_products:read` |
| `inventario.test` | Sí | `200` | tiene `perm:product-inventory-query:low_stock_products:read`, `perm:product-inventory-query:stock:read`, `perm:inventory:product-policies:read` |
| `reportes.test` | No | `403` | no tiene `perm:product-inventory-query:low_stock_products:read` |
| `consulta.test` | No | `403` | no tiene `perm:product-inventory-query:low_stock_products:read` |

Respuesta sin permiso (`403`), que no revela el permiso exigido:

```json
{
  "type": "https://sio/errors/product-inventory-query/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/companies/d22a0000-0000-4000-8000-000000000001/low-stock-products",
  "code": "PRODUCT_INVENTORY_QUERY.FORBIDDEN",
  "trace_id": "<asignado por el servicio>"
}
```

## Respuesta esperada

Estado `200`.

```json
{
  "items": [
    {
      "company_product_id": "d22e0000-0000-4000-8000-000000000007",
      "display_name": "Acetaminofén 500 mg tabletas",
      "internal_code": "P-0007",
      "base_unit": {
        "id": "d22d0000-0000-4000-8000-000000000002",
        "code": "TAB",
        "name": "Tableta"
      },
      "branch_id": "d22b0000-0000-4000-8000-000000000002",
      "base_quantity": "3.0000",
      "minimum_stock": "5.0000",
      "shortfall": "2.0000",
      "policy_status": "ACTIVE"
    }
  ],
  "page_size": 20,
  "has_next": false,
  "next_cursor": null,
  "pagination_reset": false,
  "pagination_reset_reason": null,
  "partial": false,
  "partial_reason": null,
  "sort_applied": "shortfall:desc",
  "resolved_at": "<asignado por el servicio>"
}
```
