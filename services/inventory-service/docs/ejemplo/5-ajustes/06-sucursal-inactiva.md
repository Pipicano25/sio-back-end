# Paso 6. Ajuste en una sucursal inactiva

Ejercicio 5: Ajustes de inventario.

## Llamada

`POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-adjustments`

Ejecuta: `operario.dao`.

### Solicitud

```json
{
  "adjustment_key": "d44f0500-0000-4000-8000-000000000005",
  "branch_id": "d44b0000-0000-4000-8000-000000000002",
  "company_product_id": "d44d0000-0000-4000-8000-000000000001",
  "adjustment_type": "POSITIVE",
  "quantity": "1",
  "unit_cost": "1",
  "reason": "Prueba de sucursal inactiva"
}
```

### Por qué

- El usuario es miembro `ACTIVE` de la empresa, pero la sucursal está `INACTIVE`: `BRANCH_ACCESS_DENIED`.
- Acceso por membresía (2026-11-19): la membresía da acceso a todas las sucursales activas de la empresa; la asignación a la sucursal ya no limita.

## Permiso

La URL exige `perm:inventory:adjustments:create`.

Además exige un **usuario humano** (una cuenta de servicio recibe `403` aunque tenga el permiso por comodín), miembro `ACTIVE` de la empresa y, en ajustes y conteos, que la sucursal y la empresa estén activas (lo resuelve Operational Context con el token del usuario; la asignación a la sucursal no limita). Los usuarios con el permiso no repiten la llamada en este ejercicio porque cambiaría su estado.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.sio` | Sí | `—` | tiene `perm:all:all:all`; no se repite (cambiaría el estado) |
| `admin.dao` | Sí | `—` | tiene `perm:inventory:adjustments:create`; no se repite (cambiaría el estado) |
| `operario.dao` | Sí | `403` | tiene `perm:inventory:adjustments:create` |

Respuesta sin permiso (`403`), que no revela el permiso exigido:

```json
{
  "type": "https://sio/errors/inventory/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-adjustments",
  "code": "INVENTORY.FORBIDDEN",
  "trace_id": "<asignado por Inventory>"
}
```

## Respuesta esperada

Estado `403`.

```json
{
  "type": "https://sio/errors/inventory/branch-access-denied",
  "title": "Acceso a la sucursal denegado",
  "status": 403,
  "detail": "La sucursal o la empresa no están activas. Elija una sucursal activa o solicite su reactivación al administrador de la empresa.",
  "instance": "/api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-adjustments",
  "code": "INVENTORY.BRANCH_ACCESS_DENIED",
  "trace_id": "<asignado por Inventory>"
}
```
