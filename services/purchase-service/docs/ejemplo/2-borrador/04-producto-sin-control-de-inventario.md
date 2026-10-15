# Paso 4. Agregar un producto sin control de inventario

Ejercicio 2: Compra en borrador.

## Llamada

`POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/details`

Ejecuta: `compras.test`.

### Solicitud

```json
{
  "company_product_id": "d14d0000-0000-4000-8000-000000000003",
  "company_product_presentation_id": "72733938-77e9-54a8-8ee3-060d5656abdc",
  "quantity": "1",
  "unit_cost": "50000",
  "version": 2
}
```

### Por qué

- El producto existe, pero su configuración impide comprarlo: toda compra recibida genera entrada en Inventory (P-01). Existe pero no es apto → `409`.

## Permiso

La URL exige `perm:purchase:purchase_details:create`.

Además exige un **usuario humano** (una cuenta de servicio recibe `403` aunque tenga el permiso por comodín), miembro `ACTIVE` de la empresa y, en compras, hitos, confirmación y anulación, con asignación `ACTIVE` a la sucursal de la compra (lo resuelve Operational Context con el token del usuario). Los usuarios con el permiso no repiten la llamada porque cambiaría el estado del ejercicio.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `—` | tiene `perm:all:all:all` y asignación a la sucursal; no se repite (cambiaría el estado) |
| `supervisor.test` | Sí | `—` | tiene `perm:all:all:create` y asignación a la sucursal; no se repite (cambiaría el estado) |
| `compras.test` | Sí | `409` | tiene `perm:purchase:all:all` y asignación a la sucursal |
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
  "type": "https://sio/errors/purchase/references-not-eligible",
  "title": "Referencias no aptas",
  "status": 409,
  "detail": "Una o más referencias existen, pero su estado o configuración actual impide usarlas en la compra.",
  "instance": "/api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/details",
  "code": "PURCHASE.REFERENCES_NOT_ELIGIBLE",
  "trace_id": "<asignado por el servicio>",
  "errors": [
    {
      "field": "company_product_id",
      "message": "El producto no tiene control de inventario: la compra confirmada debe generar entrada en Inventory.",
      "code": "PRODUCT_NOT_INVENTORY_CONTROLLED"
    }
  ]
}
```
