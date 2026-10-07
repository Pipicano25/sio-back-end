# Paso 6. Ajuste en una sucursal no asignada

Ejercicio 5: Ajustes de inventario.

## Llamada

`POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-adjustments`

Ejecuta: `inventario.test`.

### Solicitud

```json
{
  "adjustment_key": "d44f0500-0000-4000-8000-000000000005",
  "branch_id": "d44b0000-0000-4000-8000-000000000002",
  "company_product_id": "d44d0000-0000-4000-8000-000000000001",
  "adjustment_type": "POSITIVE",
  "quantity": "1",
  "unit_cost": "1",
  "reason": "Prueba de asignación"
}
```

### Por qué

- El usuario es miembro de la empresa pero no está asignado a esa sucursal: `BRANCH_ACCESS_DENIED`. Las consultas no exigen asignación; los ajustes y conteos sí.

## Permiso

La URL exige `perm:inventory:adjustments:create`.

Además exige un **usuario humano** (una cuenta de servicio recibe `403` aunque tenga el permiso por comodín), miembro `ACTIVE` de la empresa y, en ajustes y conteos, con asignación `ACTIVE` a la sucursal (lo resuelve Operational Context con el token del usuario). Los usuarios con el permiso no repiten la llamada en este ejercicio porque cambiaría su estado.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `—` | tiene `perm:all:all:all`; no se repite (cambiaría el estado) |
| `supervisor.test` | Sí | `—` | tiene `perm:all:all:create`; no se repite (cambiaría el estado) |
| `compras.test` | No | `403` | no tiene `perm:inventory:adjustments:create` |
| `ventas.test` | No | `403` | no tiene `perm:inventory:adjustments:create` |
| `inventario.test` | Sí | `403` | tiene `perm:inventory:adjustments:create` |
| `reportes.test` | No | `403` | no tiene `perm:inventory:adjustments:create` |
| `consulta.test` | No | `403` | no tiene `perm:inventory:adjustments:create` |

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
  "detail": "No tiene una asignación activa a la sucursal, o la sucursal o la empresa no están activas. Solicite la asignación al administrador de la empresa.",
  "instance": "/api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-adjustments",
  "code": "INVENTORY.BRANCH_ACCESS_DENIED",
  "trace_id": "<asignado por Inventory>"
}
```
