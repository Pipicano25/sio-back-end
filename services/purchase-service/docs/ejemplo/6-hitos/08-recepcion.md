# Paso 8. Registrar la recepción

Ejercicio 6: Hitos logísticos.

## Llamada

`POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/lifecycle-events`

Ejecuta: `compras.test`.

### Solicitud

```json
{
  "event_type": "RECEIVED",
  "occurred_at": "2026-11-03T16:00:00Z",
  "source": "USER"
}
```

### Por qué

- Los hitos son inmutables: un error se corrige registrando otro del mismo tipo.

## Permiso

La URL exige `perm:purchase:purchase_lifecycle_events:create`.

Además exige un **usuario humano** (una cuenta de servicio recibe `403` aunque tenga el permiso por comodín), miembro `ACTIVE` de la empresa y, en compras, hitos, confirmación y anulación, con asignación `ACTIVE` a la sucursal de la compra (lo resuelve Operational Context con el token del usuario). Los usuarios con el permiso no repiten la llamada porque cambiaría el estado del ejercicio.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `—` | tiene `perm:all:all:all` y asignación a la sucursal; no se repite (cambiaría el estado) |
| `supervisor.test` | Sí | `—` | tiene `perm:all:all:create` y asignación a la sucursal; no se repite (cambiaría el estado) |
| `compras.test` | Sí | `201` | tiene `perm:purchase:all:all` y asignación a la sucursal |
| `ventas.test` | No | `403` | no tiene `perm:purchase:purchase_lifecycle_events:create` |
| `inventario.test` | No | `403` | no tiene `perm:purchase:purchase_lifecycle_events:create` |
| `reportes.test` | No | `403` | no tiene `perm:purchase:purchase_lifecycle_events:create` |
| `consulta.test` | No | `403` | no tiene `perm:purchase:purchase_lifecycle_events:create` |

Respuesta sin permiso (`403`), que no revela el permiso exigido:

```json
{
  "type": "https://sio/errors/purchase/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/lifecycle-events",
  "code": "PURCHASE.FORBIDDEN",
  "trace_id": "<asignado por el servicio>"
}
```

## Respuesta esperada

Estado `201`.

```json
{
  "id": "<asignado por el servicio>",
  "purchase_id": "<COMPRA>",
  "event_type": "RECEIVED",
  "occurred_at": "2026-11-03T16:00:00Z",
  "recorded_by_user_id": "d14f1000-0000-4000-8000-000000000003",
  "source": "USER",
  "created_at": "<asignado por el servicio>",
  "created_by": "compras.test"
}
```
