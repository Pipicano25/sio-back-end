# Paso 3. Confirmar después de un cambio de precio

Ejercicio 4: Confirmación: precio cambiado e idempotencia.

## Llamada

`POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/confirmation`

Ejecuta: `ventas.test`.

Cabeceras: `Idempotency-Key: confirmar-venta-0001`.

Situación simulada antes de la llamada: `price:1550.00` (en la prueba automática, sobre el doble de Inventory).

### Solicitud

```json
{
  "version": 1
}
```

### Por qué

- El precio simple del arroz pasó a 1550: `409 PRICES_CHANGED` con el valor guardado y el vigente.
- Sin salida, sin número y sin cambios en el borrador.

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
  "type": "https://sio/errors/sales/prices-changed",
  "title": "Precios cambiados",
  "status": 409,
  "detail": "El precio aplicable de una o más líneas cambió desde que se guardaron. Actualice esas líneas y confirme de nuevo.",
  "instance": "/api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/confirmation",
  "code": "SALES.PRICES_CHANGED",
  "trace_id": "<asignado por el servicio>",
  "errors": [
    {
      "field": "lines[0].unit_price",
      "line_number": 1,
      "code": "PRICE_CHANGED",
      "message": "El precio aplicable de la línea cambió desde que se guardó.",
      "stored": {
        "unit_price": "1500.0000",
        "price_list_id": null,
        "price_list_item_id": null
      },
      "current": {
        "unit_price": "1550.0000",
        "price_list_id": null,
        "price_list_item_id": null
      }
    }
  ]
}
```
