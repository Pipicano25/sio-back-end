# Paso 5. Consultar como supervisor

Ejercicio 6: Rentabilidad y costo desconocido.

## Llamada

`GET /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>`

Ejecuta: `supervisor.test`.

### Por qué

- `supervisor.test` tiene `perm:sales:sales:read-profitability`: costo 1000.0000 por unidad base, costo total 3000.00, margen 1500.00 (33.3333 %).

## Permiso

La URL exige `perm:sales:sales:read`.

Además, el usuario debe ser miembro `ACTIVE` de la empresa (Operational Context, con su token). No se exige asignación a la sucursal.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `200` | tiene `perm:all:all:all` |
| `supervisor.test` | Sí | `200` | tiene `perm:all:all:read` |
| `compras.test` | No | `403` | no tiene `perm:sales:sales:read` |
| `ventas.test` | Sí | `200` | tiene `perm:sales:all:read` |
| `inventario.test` | No | `403` | no tiene `perm:sales:sales:read` |
| `reportes.test` | Sí | `200` | tiene `perm:sales:sales:read` |
| `consulta.test` | Sí | `200` | tiene `perm:sales:sales:read` |

Respuesta sin permiso (`403`), que no revela el permiso exigido:

```json
{
  "type": "https://sio/errors/sales/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>",
  "code": "SALES.FORBIDDEN",
  "trace_id": "<asignado por el servicio>"
}
```

## Respuesta esperada

Estado `200`.

```json
{
  "id": "<VENTA>",
  "company_id": "d15a0000-0000-4000-8000-000000000001",
  "branch_id": "d15b0000-0000-4000-8000-000000000001",
  "company_customer_id": "d15c0000-0000-4000-8000-000000000001",
  "customer_payment_condition_id": null,
  "payment_condition_code_snapshot": "CASH",
  "payment_terms_days_snapshot": 0,
  "due_date": "2026-11-05",
  "sale_sequence_id": "<SECUENCIA>",
  "number": "FV-202611-000001",
  "sequence_value": 1,
  "status": "CONFIRMED",
  "operation_date": "2026-11-05",
  "customer_name_snapshot": "Ana Ficticia Pérez",
  "customer_identification_snapshot": "CC 1020304050",
  "currency_code": "COP",
  "observations": null,
  "subtotal": "4500.00",
  "discount_total": "0.00",
  "tax_total": "0.00",
  "total": "4500.00",
  "has_unknown_cost": false,
  "inventory_operation_id": "<asignado por el servicio>",
  "created_by_user_id": "d15f1000-0000-4000-8000-000000000004",
  "cancelled_by_user_id": null,
  "cancelled_at": null,
  "cancellation_reason": null,
  "pending_operation_id": null,
  "version": 3,
  "created_at": "<asignado por el servicio>",
  "updated_at": "<asignado por el servicio>",
  "created_by": "ventas.test",
  "updated_by": "ventas.test",
  "lines": [
    {
      "id": "<asignado por el servicio>",
      "sale_id": "<VENTA>",
      "line_number": 1,
      "company_product_id": "d15d0000-0000-4000-8000-000000000001",
      "company_product_presentation_id": "d15e0000-0000-4000-8000-000000000002",
      "price_list_id": "d15f0000-0000-4000-8000-000000000003",
      "price_list_item_id": "d15f0000-0000-4000-8000-000000000013",
      "price_list_requested": false,
      "price_source": "PRICE_LIST_ITEM",
      "product_code_snapshot": "000045",
      "product_name_snapshot": "Arroz ficticio 500 g",
      "presentation_code_snapshot": "UND",
      "presentation_name_snapshot": "Unidad",
      "base_quantity_factor_snapshot": "1.00000000",
      "unit_code_snapshot": "UND",
      "quantity": "3.0000",
      "base_quantity": "3.0000",
      "unit_price": "1500.0000",
      "discount_amount": "0.00",
      "tax_amount": "0.00",
      "subtotal": "4500.00",
      "total": "4500.00",
      "unit_cost_snapshot": "1000.0000",
      "cost_total": "3000.00",
      "cost_known": true,
      "gross_margin_amount": "1500.00",
      "gross_margin_percentage": "33.3333",
      "created_at": "<asignado por el servicio>",
      "updated_at": "<asignado por el servicio>",
      "created_by": "ventas.test",
      "updated_by": "ventas.test"
    }
  ]
}
```
