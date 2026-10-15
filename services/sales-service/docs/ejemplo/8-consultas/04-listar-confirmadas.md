# Paso 4. Listar las ventas confirmadas

Ejercicio 8: Consultas.

## Llamada

`GET /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales?status=CONFIRMED&number=FV-202611-000001`

Ejecuta: `reportes.test`.

### Por qué

- Filtros por estado, sucursal, cliente, fechas y número; orden estable.
- `ventas.test`, `reportes.test` y `consulta.test` no tienen `perm:sales:sales:read-profitability`: en sus respuestas no aparecen costo, `cost_known`, margen ni `has_unknown_cost`.

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
  "instance": "/api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales",
  "code": "SALES.FORBIDDEN",
  "trace_id": "<asignado por el servicio>"
}
```

## Respuesta esperada

Estado `200`.

```json
{
  "items": [
    {
      "id": "<VENTA>",
      "company_id": "d15a0000-0000-4000-8000-000000000001",
      "branch_id": "d15b0000-0000-4000-8000-000000000001",
      "company_customer_id": "d15c0000-0000-4000-8000-000000000002",
      "customer_payment_condition_id": null,
      "payment_condition_code_snapshot": "CASH",
      "payment_method_id": "d15c0000-0000-4000-8000-000000000021",
      "payment_method_code_snapshot": "CASH",
      "payment_method_name_snapshot": "Efectivo",
      "payment_terms_days_snapshot": 0,
      "due_date": "2026-11-05",
      "sale_sequence_id": "<SECUENCIA>",
      "number": "FV-202611-000001",
      "sequence_value": 1,
      "status": "CONFIRMED",
      "operation_date": "2026-11-05",
      "customer_name_snapshot": "Tiendas Ficticias S.A.S.",
      "customer_identification_snapshot": "NIT 900123456",
      "currency_code": "COP",
      "observations": null,
      "subtotal": "9000.00",
      "discount_total": "0.00",
      "tax_total": "0.00",
      "total": "9000.00",
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
      "lines": null
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```
