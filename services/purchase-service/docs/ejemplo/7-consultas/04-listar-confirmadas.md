# Paso 4. Listar las compras confirmadas

Ejercicio 7: Consultas.

## Llamada

`GET /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases?status=CONFIRMED&number=CP-202611-000001`

Ejecuta: `reportes.test`.

### Por qué

- Filtros por estado, sucursal, proveedor, fechas y número; orden estable.

## Permiso

La URL exige `perm:purchase:purchases:read`.

Además, el usuario debe ser miembro `ACTIVE` de la empresa (Operational Context, con su token). No se exige asignación a la sucursal.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `200` | tiene `perm:all:all:all` |
| `supervisor.test` | Sí | `200` | tiene `perm:all:all:read` |
| `compras.test` | Sí | `200` | tiene `perm:purchase:purchases:read` |
| `ventas.test` | No | `403` | no tiene `perm:purchase:purchases:read` |
| `inventario.test` | No | `403` | no tiene `perm:purchase:purchases:read` |
| `reportes.test` | Sí | `200` | tiene `perm:purchase:purchases:read` |
| `consulta.test` | Sí | `200` | tiene `perm:purchase:purchases:read` |

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

Estado `200`.

```json
{
  "items": [
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
      "purchase_sequence_id": "<SECUENCIA>",
      "number": "CP-202611-000001",
      "sequence_value": 1,
      "status": "CONFIRMED",
      "operation_date": "2026-11-04",
      "promised_delivery_at": null,
      "supplier_document_number": null,
      "supplier_name_snapshot": "Distribuidora Ficticia S.A.S.",
      "supplier_identification_snapshot": "NIT 900123456",
      "currency_code": "COP",
      "observations": null,
      "subtotal": "9800.00",
      "discount_total": "0.00",
      "tax_total": "0.00",
      "total": "9800.00",
      "inventory_operation_id": null,
      "receipt_status": "PENDING",
      "received_at": null,
      "received_by_user_id": null,
      "created_by_user_id": "d14f1000-0000-4000-8000-000000000003",
      "cancelled_by_user_id": null,
      "cancelled_at": null,
      "cancellation_reason": null,
      "pending_operation_id": null,
      "version": 2,
      "created_at": "<asignado por el servicio>",
      "updated_at": "<asignado por el servicio>",
      "created_by": "compras.test",
      "updated_by": "compras.test",
      "lines": null
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```
