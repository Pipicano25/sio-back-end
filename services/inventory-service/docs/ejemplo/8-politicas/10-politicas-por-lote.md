# Paso 10. Política activa de varios productos (spec 022)

Ejercicio 8: Políticas de inventario.

## Llamada

`POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/branches/d44b0000-0000-4000-8000-000000000001/inventory-policies/lookup`

Ejecuta: `inventario.test`.

### Solicitud

```json
{
  "company_product_ids": [
    "d44d0000-0000-4000-8000-000000000001",
    "d44d0000-0000-4000-8000-000000000002"
  ]
}
```

### Por qué

- Hasta 100 productos en una llamada: un elemento por producto con su política **activa** o `null`.
- El aceite no tiene política: `policy: null`.

## Permiso

La URL exige `perm:inventory:product-policies:read`.

Además, el usuario debe ser miembro `ACTIVE` de la empresa y tener `perm:operational-context:application_users:read` (lo exige Operational Context al resolver su acceso). No se exige asignación a la sucursal.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `200` | tiene `perm:all:all:all` |
| `supervisor.test` | Sí | `200` | tiene `perm:all:all:read` |
| `compras.test` | No | `403` | no tiene `perm:inventory:product-policies:read` |
| `ventas.test` | No | `403` | no tiene `perm:inventory:product-policies:read` |
| `inventario.test` | Sí | `200` | tiene `perm:inventory:product-policies:read` |
| `reportes.test` | No | `403` | no tiene `perm:inventory:product-policies:read` |
| `consulta.test` | No | `403` | no tiene `perm:inventory:product-policies:read` |

Respuesta sin permiso (`403`), que no revela el permiso exigido:

```json
{
  "type": "https://sio/errors/inventory/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/companies/d44a0000-0000-4000-8000-000000000001/branches/d44b0000-0000-4000-8000-000000000001/inventory-policies/lookup",
  "code": "INVENTORY.FORBIDDEN",
  "trace_id": "<asignado por Inventory>"
}
```

## Respuesta esperada

Estado `200`.

```json
{
  "items": [
    {
      "company_product_id": "d44d0000-0000-4000-8000-000000000001",
      "policy": {
        "id": "<asignado por Inventory>",
        "minimum_stock": "5.0000",
        "status": "ACTIVE"
      }
    },
    {
      "company_product_id": "d44d0000-0000-4000-8000-000000000002",
      "policy": null
    }
  ]
}
```
