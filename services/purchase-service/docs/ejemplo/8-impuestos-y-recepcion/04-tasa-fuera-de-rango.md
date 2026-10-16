# Paso 4. Ajustar una tasa fuera de rango

Ejercicio 8: Impuesto de compra por tasa.

## Llamada

`POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/details`

Ejecuta: `supervisor.test`.

### Solicitud

```json
{
  "company_product_id": "d14d0000-0000-4000-8000-000000000001",
  "company_product_presentation_id": "86d18f28-13ae-5655-8f1e-48e6231acaa8",
  "quantity": "1",
  "unit_cost": "1000",
  "tax_percentage": "101",
  "version": 2
}
```

### Por qué

- De 0 a 100 con hasta 4 decimales: `TAX_PERCENTAGE_OUT_OF_RANGE`.

## Permiso

La URL exige `perm:purchase:purchase_details:create`.

Además exige un **usuario humano** (una cuenta de servicio recibe `403` aunque tenga el permiso por comodín), miembro `ACTIVE` de la empresa y, en compras, hitos, confirmación y anulación, con asignación `ACTIVE` a la sucursal de la compra (lo resuelve Operational Context con el token del usuario). Los usuarios con el permiso no repiten la llamada porque cambiaría el estado del ejercicio.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `—` | tiene `perm:all:all:all` y asignación a la sucursal; no se repite (cambiaría el estado) |
| `supervisor.test` | Sí | `422` | tiene `perm:all:all:create` y asignación a la sucursal |
| `compras.test` | Sí | `—` | tiene `perm:purchase:purchase_details:create` y asignación a la sucursal; no se repite (cambiaría el estado) |
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

Estado `422`.

```json
{
  "type": "https://sio/errors/purchase/validation-error",
  "title": "Solicitud inválida",
  "status": 422,
  "detail": "La solicitud contiene datos inválidos.",
  "instance": "/api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/details",
  "code": "PURCHASE.VALIDATION_ERROR",
  "trace_id": "<asignado por el servicio>",
  "errors": [
    {
      "field": "tax_percentage",
      "message": "La tasa de impuesto debe estar entre 0 y 100, con hasta 4 decimales.",
      "code": "TAX_PERCENTAGE_OUT_OF_RANGE"
    }
  ]
}
```
