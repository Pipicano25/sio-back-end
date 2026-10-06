# Paso 8. Consultar una empresa sin membresía

Ejercicio 4: Consultas de stock y kardex.

## Llamada

`GET /api/v1/companies/d44a0000-0000-4000-8000-000000000099/branches/d44b0000-0000-4000-8000-000000000001/balances`

Ejecuta: `inventario.test`.

### Por qué

- Fuera del alcance del usuario: `404` sin revelar si la empresa existe.

## Permiso

La URL exige `perm:inventory:balances:read`.

Además, el usuario debe ser miembro `ACTIVE` de la empresa y tener `perm:operational-context:application_users:read` (lo exige Operational Context al resolver su acceso). No se exige asignación a la sucursal.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `404` | tiene `perm:all:all:all` |
| `supervisor.test` | Sí | `404` | tiene `perm:all:all:read` |
| `compras.test` | No | `403` | no tiene `perm:inventory:balances:read` |
| `ventas.test` | No | `403` | no tiene `perm:inventory:balances:read` |
| `inventario.test` | Sí | `404` | tiene `perm:inventory:balances:read` |
| `reportes.test` | No | `403` | no tiene `perm:inventory:balances:read` |
| `consulta.test` | No | `403` | no tiene `perm:inventory:balances:read` |

Respuesta sin permiso (`403`), que no revela el permiso exigido:

```json
{
  "type": "https://sio/errors/inventory/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/companies/d44a0000-0000-4000-8000-000000000099/branches/d44b0000-0000-4000-8000-000000000001/balances",
  "code": "INVENTORY.FORBIDDEN",
  "trace_id": "<asignado por Inventory>"
}
```

## Respuesta esperada

Estado `404`.

```json
{
  "type": "https://sio/errors/inventory/not-found",
  "title": "Recurso no encontrado",
  "status": 404,
  "detail": "El recurso solicitado no existe o no está disponible para su usuario.",
  "instance": "/api/v1/companies/d44a0000-0000-4000-8000-000000000099/branches/d44b0000-0000-4000-8000-000000000001/balances",
  "code": "INVENTORY.NOT_FOUND",
  "trace_id": "<asignado por Inventory>"
}
```
