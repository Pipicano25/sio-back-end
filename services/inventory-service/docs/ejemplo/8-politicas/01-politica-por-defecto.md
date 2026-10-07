# Paso 1. Consultar la política sin registrarla

Ejercicio 8: Políticas de inventario.

## Llamada

`GET /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-policy`

Ejecuta: `admin.test`.

### Por qué

- Se informa la política por defecto (`PERPETUAL`, `FIFO`, `STANDARD`) con `registered: false`.

## Permiso

La URL exige `perm:inventory:company-policies:read`.

Además, el usuario debe ser miembro `ACTIVE` de la empresa y tener `perm:operational-context:application_users:read` (lo exige Operational Context al resolver su acceso). No se exige asignación a la sucursal.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `200` | tiene `perm:all:all:all` |
| `supervisor.test` | Sí | `200` | tiene `perm:all:all:read` |
| `compras.test` | No | `403` | no tiene `perm:inventory:company-policies:read` |
| `ventas.test` | No | `403` | no tiene `perm:inventory:company-policies:read` |
| `inventario.test` | Sí | `200` | tiene `perm:inventory:company-policies:read` |
| `reportes.test` | No | `403` | no tiene `perm:inventory:company-policies:read` |
| `consulta.test` | No | `403` | no tiene `perm:inventory:company-policies:read` |

Respuesta sin permiso (`403`), que no revela el permiso exigido:

```json
{
  "type": "https://sio/errors/inventory/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-policy",
  "code": "INVENTORY.FORBIDDEN",
  "trace_id": "<asignado por Inventory>"
}
```

## Respuesta esperada

Estado `200`.

```json
{
  "id": null,
  "company_id": "d44a0000-0000-4000-8000-000000000001",
  "inventory_system": "PERPETUAL",
  "valuation_method": "FIFO",
  "replenishment_strategy": "STANDARD",
  "is_active": true,
  "version": null,
  "registered": false,
  "created_at": null,
  "created_by": null,
  "updated_at": null,
  "updated_by": null
}
```
