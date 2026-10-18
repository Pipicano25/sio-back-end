# Paso 3. Sucursal de otra empresa

Ejercicio 3: Inventario multisucursal.

## Llamada

`GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/inventory-overviews?branch_id=d22b0000-0000-4000-8000-000000000099`

Ejecuta: `inventario.test`.

### Por qué

- La sucursal no es de la empresa de la ruta: `404`, igual que una empresa sin membresía.

## Permiso

La URL exige `perm:product-inventory-query:inventory_overviews:read`.

Además, el usuario debe ser miembro `ACTIVE` de la empresa (lo verifica Operational Context con su token antes de cualquier otra consulta). No se exige asignación a la sucursal.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `404` | tiene `perm:all:all:all` |
| `supervisor.test` | Sí | `404` | tiene `perm:all:all:read` |
| `compras.test` | No | `403` | no tiene `perm:product-inventory-query:inventory_overviews:read` |
| `ventas.test` | Sí | `404` | tiene `perm:product-inventory-query:inventory_overviews:read` |
| `inventario.test` | Sí | `404` | tiene `perm:product-inventory-query:inventory_overviews:read` |
| `reportes.test` | No | `403` | no tiene `perm:product-inventory-query:inventory_overviews:read` |
| `consulta.test` | No | `403` | no tiene `perm:product-inventory-query:inventory_overviews:read` |

Respuesta sin permiso (`403`), que no revela el permiso exigido:

```json
{
  "type": "https://sio/errors/product-inventory-query/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/companies/d22a0000-0000-4000-8000-000000000001/inventory-overviews",
  "code": "PRODUCT_INVENTORY_QUERY.FORBIDDEN",
  "trace_id": "<asignado por el servicio>"
}
```

## Respuesta esperada

Estado `404`.

```json
{
  "type": "https://sio/errors/product-inventory-query/not-found",
  "title": "Recurso no encontrado",
  "status": 404,
  "detail": "La empresa o la sucursal no existe o no tiene acceso.",
  "instance": "/api/v1/companies/d22a0000-0000-4000-8000-000000000001/inventory-overviews",
  "code": "PRODUCT_INVENTORY_QUERY.NOT_FOUND",
  "trace_id": "<asignado por el servicio>"
}
```
