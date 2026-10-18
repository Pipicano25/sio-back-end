# Paso 2. Evolución consolidada de la empresa

Ejercicio 4: Evolución de existencias de una sucursal.

## Llamada

`GET /api/v1/companies/d23a0000-0000-4000-8000-000000000001/reports/stock-evolution?date_from=2026-10-01&date_to=2026-10-15`

Ejecuta: `reportes.test`.

### Por qué

- Ruta de empresa: Inventory suma **por producto** las sucursales (INV-R1C, una consulta por página); nunca suma productos distintos.
- El acetaminofén aparece con `branch_count = 2` (Principal y Norte); el jarabe, con 1.
- Los días se cuentan en la zona horaria de la empresa; sin costos.

## Permisos

La URL exige `perm:business-reporting:stock_evolution:read`.

Como el servicio consulta a los propietarios **con el token del usuario**, el usuario también necesita: `perm:inventory:stock_evolution:read`, `perm:commercial-relationship:company_products:read`, `perm:product-catalog:products:read`, `perm:operational-context:application_users:read`, `perm:operational-context:branches:read`. Además debe ser miembro `ACTIVE` de la empresa (no se exige asignación a la sucursal).

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `200` | tiene `perm:all:all:all` y los permisos de lectura del propietario |
| `supervisor.test` | Sí | `200` | tiene `perm:all:all:read` y los permisos de lectura del propietario |
| `compras.test` | No | `403` | no tiene `perm:business-reporting:stock_evolution:read` |
| `ventas.test` | No | `403` | no tiene `perm:business-reporting:stock_evolution:read` |
| `inventario.test` | Sí | `200` | tiene `perm:business-reporting:stock_evolution:read` y los permisos de lectura del propietario |
| `reportes.test` | Sí | `200` | tiene `perm:business-reporting:stock_evolution:read` y los permisos de lectura del propietario |
| `consulta.test` | No | `403` | no tiene `perm:business-reporting:stock_evolution:read` |

Respuesta sin permiso (`403`), que no revela el permiso exigido:

```json
{
  "type": "https://sio/errors/business-reporting/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/companies/d23a0000-0000-4000-8000-000000000001/reports/stock-evolution",
  "code": "BUSINESS_REPORTING.FORBIDDEN",
  "trace_id": "<asignado por el servicio>"
}
```

## Respuesta

`200`

```json
{
  "report": "stock-evolution",
  "company_id": "d23a0000-0000-4000-8000-000000000001",
  "date_from": "2026-10-01",
  "date_to": "2026-10-15",
  "generated_at": "<asignado por el servicio>",
  "criteria": {
    "date_basis": "created_at",
    "from": "2026-10-01T00:00:00-05:00",
    "to": "2026-10-16T00:00:00-05:00",
    "consolidation": "by_product"
  },
  "branch_ids": [
    "d23b0000-0000-4000-8000-000000000002",
    "d23b0000-0000-4000-8000-000000000001"
  ],
  "timezone": "America/Bogota",
  "items": [
    {
      "company_product_id": "d23e0000-0000-4000-8000-000000000001",
      "product_code": "A-500",
      "product_name": "Acetaminofén 500 mg tabletas",
      "base_unit": {
        "id": "d23d0000-0000-4000-8000-000000000001",
        "code": "TAB",
        "name": "Tableta"
      },
      "opening_quantity": "550.0000",
      "entries": "1300.0000",
      "outputs": "1180.0000",
      "entry_reversals": "0.0000",
      "output_reversals": "20.0000",
      "positive_adjustments": "5.0000",
      "negative_adjustments": "12.0000",
      "closing_quantity": "683.0000",
      "movement_count": 59,
      "branch_count": 2
    },
    {
      "company_product_id": "d23e0000-0000-4000-8000-000000000002",
      "product_code": "J-120",
      "product_name": "Jarabe para la tos 120 ml",
      "base_unit": {
        "id": "d23d0000-0000-4000-8000-000000000002",
        "code": "ML",
        "name": "Mililitro"
      },
      "opening_quantity": "600.0000",
      "entries": "2400.0000",
      "outputs": "1800.0000",
      "entry_reversals": "120.0000",
      "output_reversals": "0.0000",
      "positive_adjustments": "0.0000",
      "negative_adjustments": "0.0000",
      "closing_quantity": "1080.0000",
      "movement_count": 22,
      "branch_count": 1
    }
  ],
  "page": 1,
  "page_size": 50,
  "total_records": 2,
  "total_pages": 1
}
```
