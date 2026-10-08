# Paso 5. Confirmar mientras Inventory no responde

Ejercicio 4: Confirmación: precio cambiado e idempotencia.

## Llamada

`POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/confirmation`

Ejecuta: `ventas.test`.

Cabeceras: `Idempotency-Key: confirmar-venta-0002`.

Situación simulada antes de la llamada: `inventory_down` (en la prueba automática, sobre el doble de Inventory).

### Solicitud

```json
{
  "version": 2
}
```

### Por qué

- La operación queda `PENDING` (el `operation_id` se informa) y la venta sigue en borrador sin número.
- Repetir con la **misma** clave completa la operación; el conciliador también lo haría.

## Permiso

La URL exige `perm:sales:sales:update`.

Además exige un **usuario humano** (una cuenta de servicio recibe `403` aunque tenga el permiso por comodín), miembro `ACTIVE` de la empresa y, en ventas, líneas, confirmación y anulación, con asignación `ACTIVE` a la sucursal de la venta (lo resuelve Operational Context con el token del usuario). Los usuarios con el permiso no repiten la llamada porque cambiaría el estado del ejercicio.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `—` | tiene `perm:all:all:all` y asignación a la sucursal; no se repite (cambiaría el estado) |
| `supervisor.test` | Sí | `—` | tiene `perm:all:all:update` y asignación a la sucursal; no se repite (cambiaría el estado) |
| `compras.test` | No | `403` | no tiene `perm:sales:sales:update` |
| `ventas.test` | Sí | `503` | tiene `perm:sales:all:update` y asignación a la sucursal |
| `inventario.test` | No | `403` | no tiene `perm:sales:sales:update` |
| `reportes.test` | No | `403` | no tiene `perm:sales:sales:update` |
| `consulta.test` | No | `403` | no tiene `perm:sales:sales:update` |

Respuesta sin permiso (`403`), que no revela el permiso exigido:

```json
{
  "type": "https://sio/errors/sales/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/confirmation",
  "code": "SALES.FORBIDDEN",
  "trace_id": "<asignado por el servicio>"
}
```

## Respuesta esperada

Estado `503`.

```json
{
  "type": "https://sio/errors/sales/dependency-unavailable",
  "title": "Dependencia no disponible",
  "status": 503,
  "detail": "Un servicio requerido no está disponible temporalmente. Intente de nuevo más tarde.",
  "instance": "/api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/confirmation",
  "code": "SALES.DEPENDENCY_UNAVAILABLE",
  "trace_id": "<asignado por el servicio>",
  "operation_id": "<asignado por el servicio>",
  "dependency": "inventory"
}
```
