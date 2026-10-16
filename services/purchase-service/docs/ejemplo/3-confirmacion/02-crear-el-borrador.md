# Paso 2. Crear la compra en borrador

Ejercicio 3: Confirmación y recepción idempotente.

## Llamada

`POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases`

Ejecuta: `compras.test`.

### Solicitud

```json
{
  "branch_id": "d14b0000-0000-4000-8000-000000000001",
  "company_supplier_id": "d14c0000-0000-4000-8000-000000000001",
  "operation_date": "2026-11-04",
  "payment_method_id": "d14c0000-0000-4000-8000-000000000011",
  "lines": [
    {
      "company_product_id": "d14d0000-0000-4000-8000-000000000001",
      "company_product_presentation_id": "d14e0000-0000-4000-8000-000000000001",
      "quantity": "2",
      "unit_cost": "120000"
    }
  ]
}
```

### Por qué

- Compra de contado (sin condición): `due_date` = fecha de la compra.

## Permiso

La URL exige `perm:purchase:purchases:create`.

Además exige un **usuario humano** (una cuenta de servicio recibe `403` aunque tenga el permiso por comodín), miembro `ACTIVE` de la empresa y, en compras, hitos, confirmación y anulación, con asignación `ACTIVE` a la sucursal de la compra (lo resuelve Operational Context con el token del usuario). Los usuarios con el permiso no repiten la llamada porque cambiaría el estado del ejercicio.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `—` | tiene `perm:all:all:all` y asignación a la sucursal; no se repite (cambiaría el estado) |
| `supervisor.test` | Sí | `—` | tiene `perm:all:all:create` y asignación a la sucursal; no se repite (cambiaría el estado) |
| `compras.test` | Sí | `201` | tiene `perm:purchase:purchases:create` y asignación a la sucursal |
| `ventas.test` | No | `403` | no tiene `perm:purchase:purchases:create` |
| `inventario.test` | No | `403` | no tiene `perm:purchase:purchases:create` |
| `reportes.test` | No | `403` | no tiene `perm:purchase:purchases:create` |
| `consulta.test` | No | `403` | no tiene `perm:purchase:purchases:create` |

Respuesta sin permiso (`403`), que no revela el permiso exigido:

```json
{
  "type": "https://sio/errors/purchase/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases",
  "code": "PURCHASE.FORBIDDEN",
  "trace_id": "<asignado por el servicio>"
}
```

## Respuesta esperada

Estado `201`.

```json
{
  "id": "<COMPRA>",
  "company_id": "d14a0000-0000-4000-8000-000000000001",
  "branch_id": "d14b0000-0000-4000-8000-000000000001",
  "company_supplier_id": "d14c0000-0000-4000-8000-000000000001",
  "supplier_payment_condition_id": null,
  "payment_condition_code_snapshot": "CASH",
  "payment_terms_days_snapshot": 0,
  "due_date": "2026-11-04",
  "payment_method_id": "d14c0000-0000-4000-8000-000000000011",
  "payment_method_code_snapshot": "CASH",
  "payment_method_name_snapshot": "Efectivo",
  "purchase_sequence_id": null,
  "number": null,
  "sequence_value": null,
  "status": "DRAFT",
  "operation_date": "2026-11-04",
  "promised_delivery_at": null,
  "supplier_document_number": null,
  "supplier_name_snapshot": "Distribuidora Ficticia S.A.S.",
  "supplier_identification_snapshot": "NIT 900123456",
  "currency_code": "COP",
  "observations": null,
  "subtotal": "240000.00",
  "discount_total": "0.00",
  "tax_total": "45600.00",
  "total": "285600.00",
  "inventory_operation_id": null,
  "receipt_status": null,
  "received_at": null,
  "received_by_user_id": null,
  "created_by_user_id": "d14f1000-0000-4000-8000-000000000003",
  "cancelled_by_user_id": null,
  "cancelled_at": null,
  "cancellation_reason": null,
  "pending_operation_id": null,
  "version": 1,
  "created_at": "<asignado por el servicio>",
  "updated_at": "<asignado por el servicio>",
  "created_by": "compras.test",
  "updated_by": "compras.test",
  "lines": [
    {
      "id": "<asignado por el servicio>",
      "purchase_id": "<COMPRA>",
      "line_number": 1,
      "company_product_id": "d14d0000-0000-4000-8000-000000000001",
      "company_product_presentation_id": "d14e0000-0000-4000-8000-000000000001",
      "supplier_product_id": null,
      "supplier_lead_time_snapshot_hours": null,
      "product_code_snapshot": "000045",
      "product_name_snapshot": "Arroz ficticio 500 g",
      "presentation_code_snapshot": "CAJA12",
      "presentation_name_snapshot": "Caja x12",
      "base_quantity_factor_snapshot": "12.00000000",
      "unit_code_snapshot": "UND",
      "quantity": "2.0000",
      "unit_cost": "120000.0000",
      "discount_amount": "0.00",
      "tax_amount": "45600.00",
      "tax_percentage": "19.0000",
      "tax_percentage_source": "PRODUCT_DEFAULT",
      "warnings": [],
      "subtotal": "240000.00",
      "total": "285600.00",
      "base_quantity": "24.0000",
      "inventory_unit_cost": "10000.0000",
      "created_at": "<asignado por el servicio>",
      "updated_at": "<asignado por el servicio>",
      "created_by": "compras.test",
      "updated_by": "compras.test"
    }
  ]
}
```

## Variables que se guardan

- `<COMPRA>` = `id` de la respuesta.
