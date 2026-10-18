# Paso 2. Solo las pendientes de recepción

Ejercicio 3: Compras del período.

## Llamada

`GET /api/v1/companies/d23a0000-0000-4000-8000-000000000001/reports/purchases?date_from=2026-10-01&date_to=2026-10-15&category=PENDING_RECEIPT`

Ejecuta: `reportes.test`.

### Por qué

- El filtro de categoría cambia las filas, no los totales.

## Permisos

La URL exige `perm:business-reporting:purchases:read`.

Como el servicio consulta a los propietarios **con el token del usuario**, el usuario también necesita: `perm:purchase:purchases:read`, `perm:operational-context:application_users:read`, `perm:operational-context:branches:read`. Además debe ser miembro `ACTIVE` de la empresa (no se exige asignación a la sucursal).

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `200` | tiene `perm:all:all:all` y los permisos de lectura del propietario |
| `supervisor.test` | Sí | `200` | tiene `perm:all:all:read` y los permisos de lectura del propietario |
| `compras.test` | Sí | `200` | tiene `perm:business-reporting:purchases:read` y los permisos de lectura del propietario |
| `ventas.test` | No | `403` | no tiene `perm:business-reporting:purchases:read` |
| `inventario.test` | No | `403` | no tiene `perm:business-reporting:purchases:read` |
| `reportes.test` | Sí | `200` | tiene `perm:business-reporting:purchases:read` y los permisos de lectura del propietario |
| `consulta.test` | No | `403` | no tiene `perm:business-reporting:purchases:read` |

Respuesta sin permiso (`403`), que no revela el permiso exigido:

```json
{
  "type": "https://sio/errors/business-reporting/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/companies/d23a0000-0000-4000-8000-000000000001/reports/purchases",
  "code": "BUSINESS_REPORTING.FORBIDDEN",
  "trace_id": "<asignado por el servicio>"
}
```

## Respuesta

`200`

```json
{
  "report": "purchases",
  "company_id": "d23a0000-0000-4000-8000-000000000001",
  "date_from": "2026-10-01",
  "date_to": "2026-10-15",
  "generated_at": "<asignado por el servicio>",
  "criteria": {
    "date_basis": "operation_date",
    "categories": [
      "PENDING_RECEIPT"
    ]
  },
  "branch_ids": [],
  "items": [
    {
      "purchase_id": "d2390000-0000-4000-8000-000000000002",
      "operation_date": "2026-10-09",
      "received_at": null,
      "branch_id": "d23b0000-0000-4000-8000-000000000002",
      "branch_name": "Norte",
      "supplier_name": "Laboratorio Ficticio S.A.S.",
      "supplier_identification": "Dato ficticio",
      "number": "OC-000102",
      "supplier_document_number": null,
      "status": "CONFIRMED",
      "category": "PENDING_RECEIPT",
      "receipt_status": "PENDING",
      "currency_code": "COP",
      "total": "620000.00"
    }
  ],
  "totals": [
    {
      "currency_code": "COP",
      "received_count": 1,
      "received_total": "1450000.00",
      "pending_receipt_count": 1,
      "pending_receipt_total": "620000.00",
      "cancelled_count": 1,
      "cancelled_total": "300000.00",
      "effective_total": "2070000.00"
    }
  ],
  "page": 1,
  "page_size": 50,
  "total_records": 1,
  "total_pages": 1
}
```
