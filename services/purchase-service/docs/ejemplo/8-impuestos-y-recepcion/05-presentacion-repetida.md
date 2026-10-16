# Paso 5. Agregar otra línea con la misma presentación

Ejercicio 8: Impuesto de compra por tasa.

## Llamada

`POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/details`

Ejecuta: `compras.test`.

### Solicitud

```json
{
  "company_product_id": "d14d0000-0000-4000-8000-000000000001",
  "company_product_presentation_id": "d14e0000-0000-4000-8000-000000000001",
  "quantity": "1",
  "unit_cost": "120000",
  "version": 2
}
```

### Por qué

- La caja del arroz ya está en la línea 1: `409 DUPLICATE_PRESENTATION_IN_PURCHASE`. Sume la cantidad en esa línea. Cada recepción entrega **un** costo por presentación para la actualización automática de precios (spec 021); otra presentación del mismo producto sí se admite.

## Permiso

La URL exige `perm:purchase:purchase_details:create`.

Además exige un **usuario humano** (una cuenta de servicio recibe `403` aunque tenga el permiso por comodín), miembro `ACTIVE` de la empresa y, en compras, hitos, confirmación y anulación, con asignación `ACTIVE` a la sucursal de la compra (lo resuelve Operational Context con el token del usuario). Los usuarios con el permiso no repiten la llamada porque cambiaría el estado del ejercicio.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `—` | tiene `perm:all:all:all` y asignación a la sucursal; no se repite (cambiaría el estado) |
| `supervisor.test` | Sí | `—` | tiene `perm:all:all:create` y asignación a la sucursal; no se repite (cambiaría el estado) |
| `compras.test` | Sí | `409` | tiene `perm:purchase:purchase_details:create` y asignación a la sucursal |
| `ventas.test` | No | `403` | no tiene `perm:purchase:purchase_details:create` |
| `inventario.test` | No | `403` | no tiene `perm:purchase:purchase_details:create` |
| `reportes.test` | No | `403` | no tiene `perm:purchase:purchase_details:create` |
| `consulta.test` | No | `403` | no tiene `perm:purchase:purchase_details:create` |

Respuesta sin permiso (`403`), que no revela el permiso exigido:

```json
{
  "type": "https://sio/errors/purchase/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/details",
  "code": "PURCHASE.FORBIDDEN",
  "trace_id": "<asignado por el servicio>"
}
```

## Respuesta esperada

Estado `409`.

```json
{
  "type": "https://sio/errors/purchase/duplicate-presentation-in-purchase",
  "title": "Presentación repetida en la compra",
  "status": 409,
  "detail": "La misma presentación aparece en más de una línea: agrupe la cantidad en una sola línea.",
  "instance": "/api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/details",
  "code": "PURCHASE.DUPLICATE_PRESENTATION_IN_PURCHASE",
  "trace_id": "<asignado por el servicio>",
  "errors": [
    {
      "field": "company_product_presentation_id",
      "message": "La presentación ya está en la línea 1 de la compra.",
      "code": "DUPLICATE_PRESENTATION_IN_PURCHASE",
      "company_product_presentation_id": "d14e0000-0000-4000-8000-000000000001"
    }
  ]
}
```
