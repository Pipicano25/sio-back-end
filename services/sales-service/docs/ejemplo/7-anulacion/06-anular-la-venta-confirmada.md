# Paso 6. Anular la venta confirmada

Ejercicio 7: Anulación.

## Llamada

`POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/cancellation`

Ejecuta: `ventas.test`.

Cabeceras: `Idempotency-Key: anular-0003`.

### Solicitud

```json
{
  "version": 3,
  "reason": "Cliente desistió de la compra"
}
```

### Por qué

- Sales pide a Inventory el reverso de exactamente `inventory_operation_id`: vuelven las 12 unidades con su costo.
- La venta conserva número, precio, costo y margen, y queda `CANCELLED`.

## Permiso

La URL exige `perm:sales:sales:delete`.

Además exige un **usuario humano** (una cuenta de servicio recibe `403` aunque tenga el permiso por comodín), miembro `ACTIVE` de la empresa y, en ventas, líneas, confirmación y anulación, con asignación `ACTIVE` a la sucursal de la venta (lo resuelve Operational Context con el token del usuario). Los usuarios con el permiso no repiten la llamada porque cambiaría el estado del ejercicio.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `—` | tiene `perm:all:all:all` y asignación a la sucursal; no se repite (cambiaría el estado) |
| `supervisor.test` | No | `403` | no tiene `perm:sales:sales:delete` |
| `compras.test` | No | `403` | no tiene `perm:sales:sales:delete` |
| `ventas.test` | Sí | `200` | tiene `perm:sales:all:delete` y asignación a la sucursal |
| `inventario.test` | No | `403` | no tiene `perm:sales:sales:delete` |
| `reportes.test` | No | `403` | no tiene `perm:sales:sales:delete` |
| `consulta.test` | No | `403` | no tiene `perm:sales:sales:delete` |

Respuesta sin permiso (`403`), que no revela el permiso exigido:

```json
{
  "type": "https://sio/errors/sales/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/cancellation",
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
  "status": "CANCELLED",
  "operation_date": "2026-11-05",
  "customer_name_snapshot": "Ana Ficticia Pérez",
  "customer_identification_snapshot": "CC 1020304050",
  "currency_code": "COP",
  "observations": null,
  "subtotal": "18000.00",
  "discount_total": "0.00",
  "tax_total": "0.00",
  "total": "18000.00",
  "inventory_operation_id": "<asignado por el servicio>",
  "created_by_user_id": "d15f1000-0000-4000-8000-000000000004",
  "cancelled_by_user_id": "d15f1000-0000-4000-8000-000000000004",
  "cancelled_at": "<asignado por el servicio>",
  "cancellation_reason": "Cliente desistió de la compra",
  "pending_operation_id": null,
  "version": 4,
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
      "company_product_presentation_id": "d15e0000-0000-4000-8000-000000000001",
      "price_list_id": "d15f0000-0000-4000-8000-000000000003",
      "price_list_item_id": "d15f0000-0000-4000-8000-000000000016",
      "price_list_requested": false,
      "price_source": "PRICE_LIST_ITEM",
      "product_code_snapshot": "000045",
      "product_name_snapshot": "Arroz ficticio 500 g",
      "presentation_code_snapshot": "CAJA12",
      "presentation_name_snapshot": "Caja x12",
      "base_quantity_factor_snapshot": "12.00000000",
      "unit_code_snapshot": "UND",
      "quantity": "1.0000",
      "base_quantity": "12.0000",
      "unit_price": "18000.0000",
      "discount_amount": "0.00",
      "tax_amount": "0.00",
      "subtotal": "18000.00",
      "total": "18000.00",
      "created_at": "<asignado por el servicio>",
      "updated_at": "<asignado por el servicio>",
      "created_by": "ventas.test",
      "updated_by": "ventas.test"
    }
  ]
}
```
