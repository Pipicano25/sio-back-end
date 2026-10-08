# Paso 3. Confirmar la venta

Ejercicio 5: Existencias insuficientes.

## Llamada

`POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/confirmation`

Ejecuta: `ventas.test`.

Cabeceras: `Idempotency-Key: existencias-0001`.

### Solicitud

```json
{
  "version": 1
}
```

### Por qué

- `409 INSUFFICIENT_STOCK` con el faltante por producto y líneas (disponible y requerido).
- La venta se confirma completa o no se confirma: la línea del aceite tampoco descuenta.

## Permiso

La URL exige `perm:sales:sales:update`.

Además exige un **usuario humano** (una cuenta de servicio recibe `403` aunque tenga el permiso por comodín), miembro `ACTIVE` de la empresa y, en ventas, líneas, confirmación y anulación, con asignación `ACTIVE` a la sucursal de la venta (lo resuelve Operational Context con el token del usuario). Los usuarios con el permiso no repiten la llamada porque cambiaría el estado del ejercicio.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `—` | tiene `perm:all:all:all` y asignación a la sucursal; no se repite (cambiaría el estado) |
| `supervisor.test` | Sí | `—` | tiene `perm:all:all:update` y asignación a la sucursal; no se repite (cambiaría el estado) |
| `compras.test` | No | `403` | no tiene `perm:sales:sales:update` |
| `ventas.test` | Sí | `409` | tiene `perm:sales:all:update` y asignación a la sucursal |
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

Estado `409`.

```json
{
  "type": "https://sio/errors/sales/insufficient-stock",
  "title": "Existencias insuficientes",
  "status": 409,
  "detail": "No hay existencias suficientes en la sucursal para una o más líneas. La venta no se confirmó.",
  "instance": "/api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/confirmation",
  "code": "SALES.INSUFFICIENT_STOCK",
  "trace_id": "<asignado por el servicio>",
  "shortages": [
    {
      "line_numbers": [
        1
      ],
      "company_product_id": "d15d0000-0000-4000-8000-000000000001",
      "available": "5.0000",
      "requested": "6.0000"
    }
  ]
}
```
