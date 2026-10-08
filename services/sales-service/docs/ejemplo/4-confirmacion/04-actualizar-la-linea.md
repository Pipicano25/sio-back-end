# Paso 4. Actualizar la línea con el precio vigente

Ejercicio 4: Confirmación: precio cambiado e idempotencia.

## Llamada

`PUT /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/details/<LINEA>`

Ejecuta: `ventas.test`.

### Solicitud

```json
{
  "company_product_id": "d15d0000-0000-4000-8000-000000000001",
  "quantity": "4",
  "version": 1
}
```

### Por qué

- Editar la línea vuelve a resolver su precio (1550).

## Permiso

La URL exige `perm:sales:sale_details:update`.

Además exige un **usuario humano** (una cuenta de servicio recibe `403` aunque tenga el permiso por comodín), miembro `ACTIVE` de la empresa y, en ventas, líneas, confirmación y anulación, con asignación `ACTIVE` a la sucursal de la venta (lo resuelve Operational Context con el token del usuario). Los usuarios con el permiso no repiten la llamada porque cambiaría el estado del ejercicio.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `—` | tiene `perm:all:all:all` y asignación a la sucursal; no se repite (cambiaría el estado) |
| `supervisor.test` | Sí | `—` | tiene `perm:all:all:update` y asignación a la sucursal; no se repite (cambiaría el estado) |
| `compras.test` | No | `403` | no tiene `perm:sales:sale_details:update` |
| `ventas.test` | Sí | `200` | tiene `perm:sales:all:update` y asignación a la sucursal |
| `inventario.test` | No | `403` | no tiene `perm:sales:sale_details:update` |
| `reportes.test` | No | `403` | no tiene `perm:sales:sale_details:update` |
| `consulta.test` | No | `403` | no tiene `perm:sales:sale_details:update` |

Respuesta sin permiso (`403`), que no revela el permiso exigido:

```json
{
  "type": "https://sio/errors/sales/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/details/<LINEA>",
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
  "sale_sequence_id": null,
  "number": null,
  "sequence_value": null,
  "status": "DRAFT",
  "operation_date": "2026-11-05",
  "customer_name_snapshot": "Ana Ficticia Pérez",
  "customer_identification_snapshot": "CC 1020304050",
  "currency_code": "COP",
  "observations": null,
  "subtotal": "6200.00",
  "discount_total": "0.00",
  "tax_total": "0.00",
  "total": "6200.00",
  "inventory_operation_id": null,
  "created_by_user_id": "d15f1000-0000-4000-8000-000000000004",
  "cancelled_by_user_id": null,
  "cancelled_at": null,
  "cancellation_reason": null,
  "pending_operation_id": null,
  "version": 2,
  "created_at": "<asignado por el servicio>",
  "updated_at": "<asignado por el servicio>",
  "created_by": "ventas.test",
  "updated_by": "ventas.test",
  "lines": [
    {
      "id": "<LINEA>",
      "sale_id": "<VENTA>",
      "line_number": 1,
      "company_product_id": "d15d0000-0000-4000-8000-000000000001",
      "company_product_presentation_id": null,
      "price_list_id": null,
      "price_list_item_id": null,
      "price_list_requested": false,
      "price_source": "COMPANY_PRODUCT_SALE_PRICE",
      "product_code_snapshot": "000045",
      "product_name_snapshot": "Arroz ficticio 500 g",
      "presentation_code_snapshot": null,
      "presentation_name_snapshot": null,
      "base_quantity_factor_snapshot": "1.00000000",
      "unit_code_snapshot": "UND",
      "quantity": "4.0000",
      "base_quantity": "4.0000",
      "unit_price": "1550.0000",
      "discount_amount": "0.00",
      "tax_amount": "0.00",
      "subtotal": "6200.00",
      "total": "6200.00",
      "created_at": "<asignado por el servicio>",
      "updated_at": "<asignado por el servicio>",
      "created_by": "ventas.test",
      "updated_by": "ventas.test"
    }
  ]
}
```
