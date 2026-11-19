# Paso 9. Iniciar el segundo conteo

Ejercicio 6: Conteos físicos.

## Llamada

`POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-counts/<CONTEO_2>/start`

Ejecuta: `operario.dao`.

### Solicitud

```json
{
  "version": 1
}
```

### Por qué

- `IN_PROGRESS` con `version` 2.

## Permiso

La URL exige `perm:inventory:counts:create`.

Además exige un **usuario humano** (una cuenta de servicio recibe `403` aunque tenga el permiso por comodín), miembro `ACTIVE` de la empresa y, en ajustes y conteos, que la sucursal y la empresa estén activas (lo resuelve Operational Context con el token del usuario; la asignación a la sucursal no limita). Los usuarios con el permiso no repiten la llamada en este ejercicio porque cambiaría su estado.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.sio` | Sí | `—` | tiene `perm:all:all:all`; no se repite (cambiaría el estado) |
| `admin.dao` | Sí | `—` | tiene `perm:inventory:counts:create`; no se repite (cambiaría el estado) |
| `operario.dao` | Sí | `200` | tiene `perm:inventory:counts:create` |

Respuesta sin permiso (`403`), que no revela el permiso exigido:

```json
{
  "type": "https://sio/errors/inventory/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-counts/<CONTEO_2>/start",
  "code": "INVENTORY.FORBIDDEN",
  "trace_id": "<asignado por Inventory>"
}
```

## Respuesta esperada

Estado `200`.

```json
{
  "id": "<CONTEO_2>",
  "company_id": "d44a0000-0000-4000-8000-000000000001",
  "branch_id": "d44b0000-0000-4000-8000-000000000001",
  "status": "IN_PROGRESS",
  "started_by_user_id": "d44c0000-0000-4000-8000-000000000103",
  "started_at": "<asignado por Inventory>",
  "completed_by_user_id": null,
  "completed_at": null,
  "cancelled_by_user_id": null,
  "cancelled_at": null,
  "cancel_reason": null,
  "operation_id": null,
  "observations": null,
  "version": 2,
  "created_at": "<asignado por Inventory>",
  "created_by": "operario.dao",
  "updated_at": "<asignado por Inventory>",
  "updated_by": "operario.dao",
  "details": [],
  "adjustments": []
}
```
