# Paso 6. Agregar un producto sin control de inventario

Ejercicio 2: Venta en borrador y precios.

## Llamada

`POST /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/details`

Ejecuta: `ventas.test`.

### Solicitud

```json
{
  "company_product_id": "d15d0000-0000-4000-8000-000000000003",
  "company_product_presentation_id": "d15e0000-0000-4000-8000-000000000004",
  "quantity": "1",
  "version": 2
}
```

### Por qué

- Toda venta confirmada genera una salida de inventario: el producto existe pero no es apto → `409`.

## Permiso

La URL exige `perm:sales:sale_details:create`.

Además exige un **usuario humano** (una cuenta de servicio recibe `403` aunque tenga el permiso por comodín), miembro `ACTIVE` de la empresa y, en ventas, líneas, confirmación y anulación, con asignación `ACTIVE` a la sucursal de la venta (lo resuelve Operational Context con el token del usuario). Los usuarios con el permiso no repiten la llamada porque cambiaría el estado del ejercicio.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `—` | tiene `perm:all:all:all` y asignación a la sucursal; no se repite (cambiaría el estado) |
| `supervisor.test` | Sí | `—` | tiene `perm:all:all:create` y asignación a la sucursal; no se repite (cambiaría el estado) |
| `compras.test` | No | `403` | no tiene `perm:sales:sale_details:create` |
| `ventas.test` | Sí | `409` | tiene `perm:sales:all:create` y asignación a la sucursal |
| `inventario.test` | No | `403` | no tiene `perm:sales:sale_details:create` |
| `reportes.test` | No | `403` | no tiene `perm:sales:sale_details:create` |
| `consulta.test` | No | `403` | no tiene `perm:sales:sale_details:create` |

Respuesta sin permiso (`403`), que no revela el permiso exigido:

```json
{
  "type": "https://sio/errors/sales/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/details",
  "code": "SALES.FORBIDDEN",
  "trace_id": "<asignado por el servicio>"
}
```

## Respuesta esperada

Estado `409`.

```json
{
  "type": "https://sio/errors/sales/references-not-eligible",
  "title": "Referencias no aptas",
  "status": 409,
  "detail": "Una o más referencias existen, pero su estado o configuración actual impide usarlas en la venta.",
  "instance": "/api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/details",
  "code": "SALES.REFERENCES_NOT_ELIGIBLE",
  "trace_id": "<asignado por el servicio>",
  "errors": [
    {
      "field": "company_product_id",
      "message": "El producto no tiene control de inventario: la venta confirmada debe generar salida en Inventory.",
      "code": "PRODUCT_NOT_INVENTORY_CONTROLLED"
    }
  ]
}
```
