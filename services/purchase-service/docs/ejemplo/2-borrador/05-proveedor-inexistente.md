# Paso 5. Crear una compra con un proveedor inexistente

Ejercicio 2: Compra en borrador.

## Llamada

`POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases`

Ejecuta: `compras.test`.

### Solicitud

```json
{
  "branch_id": "d14b0000-0000-4000-8000-000000000001",
  "company_supplier_id": "d14f0000-0000-4000-8000-000000000404",
  "operation_date": "2026-11-04",
  "lines": []
}
```

### Por qué

- Referencia inexistente o no resoluble → `422` (P-03).

## Permiso

La URL exige `perm:purchase:purchases:create`.

Además exige un **usuario humano** (una cuenta de servicio recibe `403` aunque tenga el permiso por comodín), miembro `ACTIVE` de la empresa y, en compras, hitos, confirmación y anulación, con asignación `ACTIVE` a la sucursal de la compra (lo resuelve Operational Context con el token del usuario). Los usuarios con el permiso no repiten la llamada porque cambiaría el estado del ejercicio.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `—` | tiene `perm:all:all:all` y asignación a la sucursal; no se repite (cambiaría el estado) |
| `supervisor.test` | Sí | `—` | tiene `perm:all:all:create` y asignación a la sucursal; no se repite (cambiaría el estado) |
| `compras.test` | Sí | `422` | tiene `perm:purchase:all:all` y asignación a la sucursal |
| `ventas.test` | No | `403` | no tiene `perm:purchase:purchases:create` |
| `inventario.test` | No | `403` | no tiene `perm:purchase:purchases:create` |
| `reportes.test` | No | `403` | no tiene `perm:purchase:purchases:create` |
| `consulta.test` | No | `403` | no tiene `perm:purchase:purchases:create` |

Respuesta sin permiso (`403`), que no revela el permiso exigido:

```json
{
  "type": "https://sio/errors/purchase/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases",
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
  "instance": "/api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases",
  "code": "PURCHASE.VALIDATION_ERROR",
  "trace_id": "<asignado por el servicio>",
  "errors": [
    {
      "field": "company_supplier_id",
      "message": "El proveedor no existe en la empresa.",
      "code": "SUPPLIER_NOT_FOUND"
    }
  ]
}
```
