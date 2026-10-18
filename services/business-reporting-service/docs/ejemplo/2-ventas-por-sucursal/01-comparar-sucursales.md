# Paso 1. Comparar las sucursales de la empresa

Ejercicio 2: Ventas por sucursal.

## Llamada

`GET /api/v1/companies/d23a0000-0000-4000-8000-000000000001/reports/sales-by-branch?date_from=2026-10-01&date_to=2026-10-15`

Ejecuta: `reportes.test`.

### Por qué

- Sin `branch_id`: todas las sucursales activas; las que no venden aparecen con cero.
- `share_percentage` es la participación sobre el total de la empresa en la misma moneda.

## Permisos

La URL exige `perm:business-reporting:sales_by_branch:read`.

Como el servicio consulta a los propietarios **con el token del usuario**, el usuario también necesita: `perm:sales:sales:read`, `perm:operational-context:application_users:read`, `perm:operational-context:branches:read`. Además debe ser miembro `ACTIVE` de la empresa (no se exige asignación a la sucursal).

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `200` | tiene `perm:all:all:all` y los permisos de lectura del propietario |
| `supervisor.test` | Sí | `200` | tiene `perm:all:all:read` y los permisos de lectura del propietario |
| `compras.test` | No | `403` | no tiene `perm:business-reporting:sales_by_branch:read` |
| `ventas.test` | No | `403` | no tiene `perm:business-reporting:sales_by_branch:read` |
| `inventario.test` | No | `403` | no tiene `perm:business-reporting:sales_by_branch:read` |
| `reportes.test` | Sí | `200` | tiene `perm:business-reporting:sales_by_branch:read` y los permisos de lectura del propietario |
| `consulta.test` | No | `403` | no tiene `perm:business-reporting:sales_by_branch:read` |

Respuesta sin permiso (`403`), que no revela el permiso exigido:

```json
{
  "type": "https://sio/errors/business-reporting/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/companies/d23a0000-0000-4000-8000-000000000001/reports/sales-by-branch",
  "code": "BUSINESS_REPORTING.FORBIDDEN",
  "trace_id": "<asignado por el servicio>"
}
```

## Respuesta

`200`

```json
{
  "report": "sales-by-branch",
  "company_id": "d23a0000-0000-4000-8000-000000000001",
  "date_from": "2026-10-01",
  "date_to": "2026-10-15",
  "generated_at": "<asignado por el servicio>",
  "criteria": {
    "sales_status": "CONFIRMED",
    "date_basis": "operation_date"
  },
  "branch_ids": [],
  "items": [
    {
      "branch_id": "d23b0000-0000-4000-8000-000000000001",
      "branch_code": "PPAL",
      "branch_name": "Principal",
      "currency_code": "COP",
      "sales_count": 80,
      "total_amount": "820750.00",
      "share_percentage": "70.0000"
    },
    {
      "branch_id": "d23b0000-0000-4000-8000-000000000002",
      "branch_code": "NORTE",
      "branch_name": "Norte",
      "currency_code": "COP",
      "sales_count": 40,
      "total_amount": "351750.00",
      "share_percentage": "30.0000"
    }
  ],
  "totals": [
    {
      "currency_code": "COP",
      "sales_count": 120,
      "total_amount": "1172500.00"
    }
  ]
}
```
