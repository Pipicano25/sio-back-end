# Paso 1. Ranking por cantidad en unidad base

Ejercicio 1: Productos más vendidos.

## Llamada

`GET /api/v1/companies/d23a0000-0000-4000-8000-000000000001/reports/top-selling-products?date_from=2026-10-01&date_to=2026-10-15`

Ejecuta: `reportes.test`.

### Por qué

- Sin `rank_by`: se ordena por cantidad vendida en la unidad base de cada producto (DR-04).
- Solo ventas `CONFIRMED` por `operation_date`; las anuladas no cuentan (DR-01).
- `mixed_base_units = true`: el jarabe (ml) y las tabletas no son comparables entre sí; nunca se suman cantidades de productos distintos.

## Permisos

La URL exige `perm:business-reporting:top_selling_products:read`.

Como el servicio consulta a los propietarios **con el token del usuario**, el usuario también necesita: `perm:sales:sales:read`, `perm:commercial-relationship:company_products:read`, `perm:product-catalog:products:read`, `perm:operational-context:application_users:read`, `perm:operational-context:branches:read`. Además debe ser miembro `ACTIVE` de la empresa (no se exige asignación a la sucursal).

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `200` | tiene `perm:all:all:all` y los permisos de lectura del propietario |
| `supervisor.test` | Sí | `200` | tiene `perm:all:all:read` y los permisos de lectura del propietario |
| `compras.test` | No | `403` | no tiene `perm:business-reporting:top_selling_products:read` |
| `ventas.test` | Sí | `200` | tiene `perm:business-reporting:top_selling_products:read` y los permisos de lectura del propietario |
| `inventario.test` | No | `403` | no tiene `perm:business-reporting:top_selling_products:read` |
| `reportes.test` | Sí | `200` | tiene `perm:business-reporting:top_selling_products:read` y los permisos de lectura del propietario |
| `consulta.test` | No | `403` | no tiene `perm:business-reporting:top_selling_products:read` |

Respuesta sin permiso (`403`), que no revela el permiso exigido:

```json
{
  "type": "https://sio/errors/business-reporting/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/companies/d23a0000-0000-4000-8000-000000000001/reports/top-selling-products",
  "code": "BUSINESS_REPORTING.FORBIDDEN",
  "trace_id": "<asignado por el servicio>"
}
```

## Respuesta

`200`

```json
{
  "report": "top-selling-products",
  "company_id": "d23a0000-0000-4000-8000-000000000001",
  "date_from": "2026-10-01",
  "date_to": "2026-10-15",
  "generated_at": "<asignado por el servicio>",
  "criteria": {
    "sales_status": "CONFIRMED",
    "date_basis": "operation_date",
    "rank_by": "quantity"
  },
  "branch_ids": [],
  "mixed_base_units": true,
  "items": [
    {
      "rank": 1,
      "company_product_id": "d23e0000-0000-4000-8000-000000000002",
      "product_code": "J-120",
      "product_name": "Jarabe para la tos 120 ml",
      "base_unit": {
        "id": "d23d0000-0000-4000-8000-000000000002",
        "code": "ML",
        "name": "Mililitro"
      },
      "quantity_base": "2400.0000",
      "currency_code": "COP",
      "amount": "380000.00",
      "sales_count": 19,
      "presentations": null
    },
    {
      "rank": 2,
      "company_product_id": "d23e0000-0000-4000-8000-000000000001",
      "product_code": "A-500",
      "product_name": "Acetaminofén 500 mg tabletas",
      "base_unit": {
        "id": "d23d0000-0000-4000-8000-000000000001",
        "code": "TAB",
        "name": "Tableta"
      },
      "quantity_base": "1250.0000",
      "currency_code": "COP",
      "amount": "612500.00",
      "sales_count": 84,
      "presentations": null
    },
    {
      "rank": 3,
      "company_product_id": "d23e0000-0000-4000-8000-000000000003",
      "product_code": "C-100",
      "product_name": "Crema dental 100 ml",
      "base_unit": {
        "id": "d23d0000-0000-4000-8000-000000000003",
        "code": "UND",
        "name": "Unidad"
      },
      "quantity_base": "40.0000",
      "currency_code": "COP",
      "amount": "180000.00",
      "sales_count": 31,
      "presentations": null
    }
  ],
  "totals": [
    {
      "currency_code": "COP",
      "amount": "1172500.00",
      "sales_count": 120
    }
  ]
}
```
