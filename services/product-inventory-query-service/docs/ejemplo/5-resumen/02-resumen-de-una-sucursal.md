# Paso 2. Resumen de una sucursal

Ejercicio 5: Resumen de inventario.

## Llamada

`GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/inventory-summary?branch_id=d22b0000-0000-4000-8000-000000000002`

Ejecuta: `supervisor.test`.

### Por qué

- Solo NORTE; `adopted_products` sigue siendo de la empresa.
- Tampoco `supervisor.test` recibe valoración ni costos: el servicio no los devuelve a nadie.

## Permiso

La URL exige `perm:product-inventory-query:inventory_summary:read`.

Además, el usuario debe ser miembro `ACTIVE` de la empresa (lo verifica Operational Context con su token antes de cualquier otra consulta). No se exige asignación a la sucursal.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `200` | tiene `perm:all:all:all` |
| `supervisor.test` | Sí | `200` | tiene `perm:all:all:read` |
| `compras.test` | No | `403` | no tiene `perm:product-inventory-query:inventory_summary:read` |
| `ventas.test` | No | `403` | no tiene `perm:product-inventory-query:inventory_summary:read` |
| `inventario.test` | Sí | `200` | tiene `perm:product-inventory-query:inventory_summary:read` |
| `reportes.test` | No | `403` | no tiene `perm:product-inventory-query:inventory_summary:read` |
| `consulta.test` | No | `403` | no tiene `perm:product-inventory-query:inventory_summary:read` |

Respuesta sin permiso (`403`), que no revela el permiso exigido:

```json
{
  "type": "https://sio/errors/product-inventory-query/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/companies/d22a0000-0000-4000-8000-000000000001/inventory-summary",
  "code": "PRODUCT_INVENTORY_QUERY.FORBIDDEN",
  "trace_id": "<asignado por el servicio>"
}
```

## Respuesta esperada

Estado `200`.

```json
{
  "company_id": "d22a0000-0000-4000-8000-000000000001",
  "resolved_at": "<asignado por el servicio>",
  "adopted_products": 8,
  "branches": [
    {
      "branch_id": "d22b0000-0000-4000-8000-000000000002",
      "products_with_positive_balance": 1,
      "products_with_zero_balance": 1,
      "products_with_policy": 1,
      "products_below_minimum": 1
    }
  ],
  "consolidated": {
    "products_with_positive_balance": 1,
    "products_with_zero_balance": 1,
    "products_with_policy": 1,
    "products_below_minimum": 1
  }
}
```
