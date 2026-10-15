# Paso 8. Registrar el hito de recepción antes de recibir

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

- Spec 020: el hito `RECEIVED` exige la recepción física confirmada (`PURCHASE_NOT_RECEIVED`).

## Permiso

La URL exige `perm:purchase:purchase_lifecycle_events:create`.

Además exige un **usuario humano** (una cuenta de servicio recibe `403` aunque tenga el permiso por comodín), miembro `ACTIVE` de la empresa y, en compras, hitos, confirmación y anulación, con asignación `ACTIVE` a la sucursal de la compra (lo resuelve Operational Context con el token del usuario). Los usuarios con el permiso no repiten la llamada porque cambiaría el estado del ejercicio.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `—` | tiene `perm:all:all:all` y asignación a la sucursal; no se repite (cambiaría el estado) |
| `supervisor.test` | Sí | `—` | tiene `perm:all:all:create` y asignación a la sucursal; no se repite (cambiaría el estado) |
| `compras.test` | Sí | `409` | tiene `perm:purchase:all:all` y asignación a la sucursal |
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

Estado `409`.

```json
{
  "type": "https://sio/errors/purchase/purchase-not-received",
  "title": "Compra pendiente de recepción",
  "status": 409,
  "detail": "El hito RECEIVED exige que la recepción física de la compra esté confirmada.",
  "instance": "/api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/lifecycle-events",
  "code": "PURCHASE.PURCHASE_NOT_RECEIVED",
  "trace_id": "<asignado por el servicio>",
  "event_type": "RECEIVED"
}
```
