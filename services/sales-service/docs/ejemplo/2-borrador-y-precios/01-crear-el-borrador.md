# Paso 1. Crear la venta en borrador

Ejercicio 2: Venta en borrador y precios.

## Llamada

`POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales`

Ejecuta: `ventas.test`.

### Solicitud

```json
{
  "branch_id": "d15b0000-0000-4000-8000-000000000001",
  "company_customer_id": "d15c0000-0000-4000-8000-000000000001",
  "lines": [
    {
      "company_product_id": "d15d0000-0000-4000-8000-000000000001",
      "company_product_presentation_id": "d15e0000-0000-4000-8000-000000000001",
      "quantity": "2",
      "price_list_id": "d15f0000-0000-4000-8000-000000000001",
      "tax_amount": "5700"
    },
    {
      "company_product_id": "d15d0000-0000-4000-8000-000000000002",
      "company_product_presentation_id": "d15e0000-0000-4000-8000-000000000003",
      "quantity": "3",
      "discount_amount": "300"
    }
  ]
}
```

### Por qué

- La primera línea pide la lista mayorista: precio de la caja 16000 (`price_list_requested = true`).
- La segunda no pide lista: se usa el precio de la unidad de aceite en la lista predeterminada GENERAL (9000).
- Solo contado: `CASH`, sin plazo, `due_date` = `operation_date` = hoy en la zona de la sucursal.
- El borrador no afecta inventario y no tiene número.

## Permiso

La URL exige `perm:sales:sales:create`.

Además exige un **usuario humano** (una cuenta de servicio recibe `403` aunque tenga el permiso por comodín), miembro `ACTIVE` de la empresa y, en ventas, líneas, confirmación y anulación, con asignación `ACTIVE` a la sucursal de la venta (lo resuelve Operational Context con el token del usuario). Los usuarios con el permiso no repiten la llamada porque cambiaría el estado del ejercicio.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `—` | tiene `perm:all:all:all` y asignación a la sucursal; no se repite (cambiaría el estado) |
| `supervisor.test` | Sí | `—` | tiene `perm:all:all:create` y asignación a la sucursal; no se repite (cambiaría el estado) |
| `compras.test` | No | `403` | no tiene `perm:sales:sales:create` |
| `ventas.test` | Sí | `201` | tiene `perm:sales:all:create` y asignación a la sucursal |
| `inventario.test` | No | `403` | no tiene `perm:sales:sales:create` |
| `reportes.test` | No | `403` | no tiene `perm:sales:sales:create` |
| `consulta.test` | No | `403` | no tiene `perm:sales:sales:create` |

Respuesta sin permiso (`403`), que no revela el permiso exigido:

```json
{
  "type": "https://sio/errors/sales/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales",
  "code": "SALES.FORBIDDEN",
  "trace_id": "<asignado por el servicio>"
}
```

## Respuesta esperada

Estado `201`.

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
  "subtotal": "59000.00",
  "discount_total": "300.00",
  "tax_total": "5700.00",
  "total": "64400.00",
  "inventory_operation_id": null,
  "created_by_user_id": "d15f1000-0000-4000-8000-000000000004",
  "cancelled_by_user_id": null,
  "cancelled_at": null,
  "cancellation_reason": null,
  "pending_operation_id": null,
  "version": 1,
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
      "price_list_id": "d15f0000-0000-4000-8000-000000000001",
      "price_list_item_id": "d15f0000-0000-4000-8000-000000000011",
      "price_list_requested": true,
      "price_source": "PRICE_LIST_ITEM",
      "product_code_snapshot": "000045",
      "product_name_snapshot": "Arroz ficticio 500 g",
      "presentation_code_snapshot": "CAJA12",
      "presentation_name_snapshot": "Caja x12",
      "base_quantity_factor_snapshot": "12.00000000",
      "unit_code_snapshot": "UND",
      "quantity": "2.0000",
      "base_quantity": "24.0000",
      "unit_price": "16000.0000",
      "discount_amount": "0.00",
      "tax_amount": "5700.00",
      "subtotal": "32000.00",
      "total": "37700.00",
      "created_at": "<asignado por el servicio>",
      "updated_at": "<asignado por el servicio>",
      "created_by": "ventas.test",
      "updated_by": "ventas.test"
    },
    {
      "id": "<asignado por el servicio>",
      "sale_id": "<VENTA>",
      "line_number": 2,
      "company_product_id": "d15d0000-0000-4000-8000-000000000002",
      "company_product_presentation_id": "d15e0000-0000-4000-8000-000000000003",
      "price_list_id": "d15f0000-0000-4000-8000-000000000003",
      "price_list_item_id": "d15f0000-0000-4000-8000-000000000014",
      "price_list_requested": false,
      "price_source": "PRICE_LIST_ITEM",
      "product_code_snapshot": "000046",
      "product_name_snapshot": "Aceite ficticio 1 L",
      "presentation_code_snapshot": "UND",
      "presentation_name_snapshot": "Unidad",
      "base_quantity_factor_snapshot": "1.00000000",
      "unit_code_snapshot": "UND",
      "quantity": "3.0000",
      "base_quantity": "3.0000",
      "unit_price": "9000.0000",
      "discount_amount": "300.00",
      "tax_amount": "0.00",
      "subtotal": "27000.00",
      "total": "26700.00",
      "created_at": "<asignado por el servicio>",
      "updated_at": "<asignado por el servicio>",
      "created_by": "ventas.test",
      "updated_by": "ventas.test"
    }
  ]
}
```

## Variables que se guardan

- `<VENTA>` = `id` de la respuesta.
