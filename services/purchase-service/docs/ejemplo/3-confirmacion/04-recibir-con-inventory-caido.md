# Paso 4. Confirmar la recepción mientras Inventory no responde

Ejercicio 3: Confirmación y recepción idempotente.

## Llamada

`POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/receipt`

Ejecuta: `compras.test`.

Cabeceras: `Idempotency-Key: recibir-compra-0001`.

Situación simulada antes de la llamada: `inventory_down` (en la prueba automática, sobre el doble de Inventory).

### Solicitud

```json
{
  "version": "<VERSION_CONFIRMADA>",
  "full_receipt_confirmed": true
}
```

### Por qué

- `full_receipt_confirmed = true`: el usuario declara que recibió **toda** la mercancía.
- La operación de recepción queda `PENDING` (el `operation_id` se informa) y la compra sigue pendiente.
- Repetir con la **misma** clave completa la operación; el conciliador también lo haría.

## Permiso

La URL exige `perm:purchase:purchases:update`.

Además exige un **usuario humano** (una cuenta de servicio recibe `403` aunque tenga el permiso por comodín), miembro `ACTIVE` de la empresa y, en compras, hitos, confirmación y anulación, con asignación `ACTIVE` a la sucursal de la compra (lo resuelve Operational Context con el token del usuario). Los usuarios con el permiso no repiten la llamada porque cambiaría el estado del ejercicio.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `—` | tiene `perm:all:all:all` y asignación a la sucursal; no se repite (cambiaría el estado) |
| `supervisor.test` | Sí | `—` | tiene `perm:all:all:update` y asignación a la sucursal; no se repite (cambiaría el estado) |
| `compras.test` | Sí | `503` | tiene `perm:purchase:all:all` y asignación a la sucursal |
| `ventas.test` | No | `403` | no tiene `perm:purchase:purchases:update` |
| `inventario.test` | No | `403` | no tiene `perm:purchase:purchases:update` |
| `reportes.test` | No | `403` | no tiene `perm:purchase:purchases:update` |
| `consulta.test` | No | `403` | no tiene `perm:purchase:purchases:update` |

Respuesta sin permiso (`403`), que no revela el permiso exigido:

```json
{
  "type": "https://sio/errors/purchase/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/receipt",
  "code": "PURCHASE.FORBIDDEN",
  "trace_id": "<asignado por el servicio>"
}
```

## Respuesta esperada

Estado `503`.

```json
{
  "type": "https://sio/errors/purchase/dependency-unavailable",
  "title": "Dependencia no disponible",
  "status": 503,
  "detail": "Un servicio requerido no está disponible temporalmente. Intente de nuevo más tarde.",
  "instance": "/api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/receipt",
  "code": "PURCHASE.DEPENDENCY_UNAVAILABLE",
  "trace_id": "<asignado por el servicio>",
  "operation_id": "<asignado por el servicio>",
  "dependency": "inventory"
}
```
