# Paso 2. Consultar las secuencias de la empresa

Ejercicio 1: Secuencias de numeración.

## Llamada

`GET /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchase-sequences`

Ejecuta: `compras.test`.

### Por qué

- Los contadores por período aparecen cuando se confirma la primera compra del período.

## Permiso

La URL exige `perm:purchase:purchase_sequences:read`.

Además, el usuario debe ser miembro `ACTIVE` de la empresa (Operational Context, con su token). No se exige asignación a la sucursal.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `200` | tiene `perm:all:all:all` |
| `supervisor.test` | Sí | `200` | tiene `perm:all:all:read` |
| `compras.test` | Sí | `200` | tiene `perm:purchase:purchase_sequences:read` |
| `ventas.test` | No | `403` | no tiene `perm:purchase:purchase_sequences:read` |
| `inventario.test` | No | `403` | no tiene `perm:purchase:purchase_sequences:read` |
| `reportes.test` | Sí | `200` | tiene `perm:purchase:purchase_sequences:read` |
| `consulta.test` | Sí | `200` | tiene `perm:purchase:purchase_sequences:read` |

Respuesta sin permiso (`403`), que no revela el permiso exigido:

```json
{
  "type": "https://sio/errors/purchase/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchase-sequences",
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
      "id": "<SECUENCIA>",
      "company_id": "d14a0000-0000-4000-8000-000000000001",
      "branch_id": null,
      "document_kind": "PURCHASE",
      "series_code": "PRINCIPAL",
      "prefix": "CP",
      "separator": "-",
      "initial_number": 1,
      "maximum_number": null,
      "number_length": 6,
      "reset_policy": "MONTHLY",
      "is_active": true,
      "version": 1,
      "created_at": "<asignado por el servicio>",
      "updated_at": "<asignado por el servicio>",
      "created_by": "compras.test",
      "updated_by": "compras.test",
      "counters": []
    }
  ]
}
```
