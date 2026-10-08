# Paso 5. Consultar una venta desde otra empresa

Ejercicio 8: Consultas.

## Llamada

`GET /api/v1/companies/d15a0000-0000-4000-8000-000000000099/sales/<VENTA>`

Ejecuta: `reportes.test`.

### Por qué

- Sin membresía en esa empresa: `404`, igual que un recurso inexistente.

## Permiso

La URL exige `perm:sales:sales:read`.

Además, el usuario debe ser miembro `ACTIVE` de la empresa (Operational Context, con su token). No se exige asignación a la sucursal.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `404` | tiene `perm:all:all:all` |
| `supervisor.test` | Sí | `404` | tiene `perm:all:all:read` |
| `compras.test` | No | `403` | no tiene `perm:sales:sales:read` |
| `ventas.test` | Sí | `404` | tiene `perm:sales:all:read` |
| `inventario.test` | No | `403` | no tiene `perm:sales:sales:read` |
| `reportes.test` | Sí | `404` | tiene `perm:sales:sales:read` |
| `consulta.test` | Sí | `404` | tiene `perm:sales:sales:read` |

Respuesta sin permiso (`403`), que no revela el permiso exigido:

```json
{
  "type": "https://sio/errors/sales/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/companies/d15a0000-0000-4000-8000-000000000099/sales/<VENTA>",
  "code": "SALES.FORBIDDEN",
  "trace_id": "<asignado por el servicio>"
}
```

## Respuesta esperada

Estado `404`.

```json
{
  "type": "https://sio/errors/sales/not-found",
  "title": "Recurso no encontrado",
  "status": 404,
  "detail": "El recurso solicitado no existe o no está disponible para su usuario.",
  "instance": "/api/v1/companies/d15a0000-0000-4000-8000-000000000099/sales/<VENTA>",
  "code": "SALES.NOT_FOUND",
  "trace_id": "<asignado por el servicio>"
}
```
