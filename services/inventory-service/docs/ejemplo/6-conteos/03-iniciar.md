# Paso 3. Iniciar el conteo

Ejercicio 6: Conteos físicos.

## Llamada

`POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-counts/<CONTEO>/start`

Ejecuta: `inventario.test`.

### Solicitud

```json
{
  "version": 1
}
```

### Por qué

- Pasa a `IN_PROGRESS` (`version` 2). Solo un conteo en curso por sucursal.

## Permiso

La URL exige `perm:inventory:counts:create`.

Además exige un **usuario humano** (una cuenta de servicio recibe `403` aunque tenga el permiso por comodín), miembro `ACTIVE` de la empresa y, en ajustes y conteos, con asignación `ACTIVE` a la sucursal (lo resuelve Operational Context con el token del usuario). Los usuarios con el permiso no repiten la llamada en este ejercicio porque cambiaría su estado.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `—` | tiene `perm:all:all:all`; no se repite (cambiaría el estado) |
| `supervisor.test` | Sí | `—` | tiene `perm:all:all:create`; no se repite (cambiaría el estado) |
| `compras.test` | No | `403` | no tiene `perm:inventory:counts:create` |
| `ventas.test` | No | `403` | no tiene `perm:inventory:counts:create` |
| `inventario.test` | Sí | `200` | tiene `perm:inventory:counts:create` |
| `reportes.test` | No | `403` | no tiene `perm:inventory:counts:create` |
| `consulta.test` | No | `403` | no tiene `perm:inventory:counts:create` |

Respuesta sin permiso (`403`), que no revela el permiso exigido:

```json
{
  "type": "https://sio/errors/inventory/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-counts/<CONTEO>/start",
  "code": "INVENTORY.FORBIDDEN",
  "trace_id": "<asignado por Inventory>"
}
```

## Respuesta esperada

Estado `200`.

```json
{
  "id": "<CONTEO>",
  "company_id": "d44a0000-0000-4000-8000-000000000001",
  "branch_id": "d44b0000-0000-4000-8000-000000000001",
  "status": "IN_PROGRESS",
  "started_by_user_id": "d44c0000-0000-4000-8000-000000000105",
  "started_at": "<asignado por Inventory>",
  "completed_by_user_id": null,
  "completed_at": null,
  "cancelled_by_user_id": null,
  "cancelled_at": null,
  "cancel_reason": null,
  "operation_id": null,
  "observations": "Conteo mensual ficticio",
  "version": 2,
  "created_at": "<asignado por Inventory>",
  "created_by": "inventario.test",
  "updated_at": "<asignado por Inventory>",
  "updated_by": "inventario.test",
  "details": [],
  "adjustments": []
}
```
