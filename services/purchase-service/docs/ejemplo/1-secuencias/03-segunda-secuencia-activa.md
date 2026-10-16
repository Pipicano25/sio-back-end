# Paso 3. Intentar una segunda secuencia activa

Ejercicio 1: Secuencias de numeración.

## Llamada

`POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchase-sequences`

Ejecuta: `compras.test`.

### Solicitud

```json
{
  "series_code": "ALTERNA",
  "prefix": "CA",
  "separator": "-",
  "initial_number": 1,
  "number_length": 6,
  "reset_policy": "MONTHLY"
}
```

### Por qué

- A lo sumo una secuencia activa por empresa, sucursal y tipo de documento (P-02).
- Para cambiar de secuencia se desactiva primero la vigente.

## Permiso

La URL exige `perm:purchase:purchase_sequences:create`.

Además exige un **usuario humano** (una cuenta de servicio recibe `403` aunque tenga el permiso por comodín), miembro `ACTIVE` de la empresa y, en compras, hitos, confirmación y anulación, con asignación `ACTIVE` a la sucursal de la compra (lo resuelve Operational Context con el token del usuario). Los usuarios con el permiso no repiten la llamada porque cambiaría el estado del ejercicio.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `—` | tiene `perm:all:all:all` y asignación a la sucursal; no se repite (cambiaría el estado) |
| `supervisor.test` | Sí | `—` | tiene `perm:all:all:create` y asignación a la sucursal; no se repite (cambiaría el estado) |
| `compras.test` | Sí | `409` | tiene `perm:purchase:purchase_sequences:create` y asignación a la sucursal |
| `ventas.test` | No | `403` | no tiene `perm:purchase:purchase_sequences:create` |
| `inventario.test` | No | `403` | no tiene `perm:purchase:purchase_sequences:create` |
| `reportes.test` | No | `403` | no tiene `perm:purchase:purchase_sequences:create` |
| `consulta.test` | No | `403` | no tiene `perm:purchase:purchase_sequences:create` |

Respuesta sin permiso (`403`), que no revela el permiso exigido:

```json
{
  "type": "https://sio/errors/purchase/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchase-sequences",
  "code": "PURCHASE.FORBIDDEN",
  "trace_id": "<asignado por el servicio>"
}
```

## Respuesta esperada

Estado `409`.

```json
{
  "type": "https://sio/errors/purchase/sequence-already-active",
  "title": "Secuencia activa existente",
  "status": 409,
  "detail": "Ya existe una secuencia activa para la empresa, la sucursal y el tipo de documento. Desactívela antes.",
  "instance": "/api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchase-sequences",
  "code": "PURCHASE.SEQUENCE_ALREADY_ACTIVE",
  "trace_id": "<asignado por el servicio>"
}
```
