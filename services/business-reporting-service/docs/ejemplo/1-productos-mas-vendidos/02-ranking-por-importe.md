# Paso 2. Ranking por importe con presentaciones

Ejercicio 1: Productos más vendidos.

## Llamada

`GET /api/v1/companies/d23a0000-0000-4000-8000-000000000001/reports/top-selling-products?date_from=2026-10-01&date_to=2026-10-15&rank_by=amount&include_presentations=true&limit=2`

Ejecuta: `ventas.test`.

### Por qué

- `rank_by=amount` ordena por importe dentro de la moneda.
- `include_presentations=true` muestra cómo se agrupan las presentaciones en la unidad base con el factor guardado en cada venta (Caja x 10 → 10 tabletas).

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
    "rank_by": "amount"
  },
  "branch_ids": [],
  "mixed_base_units": true,
  "items": [
    {
      "rank": 1,
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
      "presentations": [
        {
          "company_product_presentation_id": "d23c0000-0000-4000-8000-000000000001",
          "code": "CJ10",
          "name": "Caja x 10",
          "quantity": "100.0000",
          "quantity_base": "1000.0000",
          "amount": "490000.00"
        },
        {
          "company_product_presentation_id": "d23c0000-0000-4000-8000-000000000002",
          "code": "TAB",
          "name": "Tableta",
          "quantity": "250.0000",
          "quantity_base": "250.0000",
          "amount": "122500.00"
        }
      ]
    },
    {
      "rank": 2,
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
      "presentations": [
        {
          "company_product_presentation_id": "d23c0000-0000-4000-8000-000000000003",
          "code": "FR",
          "name": "Frasco 120 ml",
          "quantity": "20.0000",
          "quantity_base": "2400.0000",
          "amount": "380000.00"
        }
      ]
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
