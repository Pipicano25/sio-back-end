# Paso 1. Resumen de la empresa

Ejercicio 5: Resumen de inventario.

## Llamada

`GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/inventory-summary`

Ejecuta: `inventario.test`.

### Por qué

- `adopted_products` cuenta los productos `ACTIVE` con control de inventario (8): excluye el servicio (sin control) y el producto inactivo.
- Inventory cuenta por saldo: el servicio y el producto inactivo tienen saldo y sí cuentan con saldo positivo; un producto sin registro de saldo no cuenta en ningún indicador.
- Ningún indicador se calcula restando datos de Commercial Relationship e Inventory.

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
      "branch_id": "d22b0000-0000-4000-8000-000000000001",
      "products_with_positive_balance": 3,
      "products_with_zero_balance": 1,
      "products_with_policy": 3,
      "products_below_minimum": 1
    },
    {
      "branch_id": "d22b0000-0000-4000-8000-000000000002",
      "products_with_positive_balance": 1,
      "products_with_zero_balance": 1,
      "products_with_policy": 1,
      "products_below_minimum": 1
    },
    {
      "branch_id": "d22b0000-0000-4000-8000-000000000003",
      "products_with_positive_balance": 1,
      "products_with_zero_balance": 0,
      "products_with_policy": 0,
      "products_below_minimum": 0
    }
  ],
  "consolidated": {
    "products_with_positive_balance": 4,
    "products_with_zero_balance": 1,
    "products_with_policy": 3,
    "products_below_minimum": 2
  }
}
```
