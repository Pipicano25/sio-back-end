# Paso 5. Cursor alterado

Ejercicio 2: Cambio de filtros y cursor.

## Llamada

`GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/product-overviews?search=Colgate&page_size=2&cursor=v1.eyJ9.firma-alterada`

Ejecuta: `ventas.test`.

### Por qué

- La firma no corresponde: `INVALID_CURSOR`, sin resultados y sin decir qué falló.

## Permiso

La URL exige `perm:product-inventory-query:product_overviews:read`.

Además, el usuario debe ser miembro `ACTIVE` de la empresa (lo verifica Operational Context con su token antes de cualquier otra consulta). No se exige asignación a la sucursal.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `422` | tiene `perm:all:all:all` |
| `supervisor.test` | Sí | `422` | tiene `perm:all:all:read` |
| `compras.test` | No | `403` | no tiene `perm:product-inventory-query:product_overviews:read` |
| `ventas.test` | Sí | `422` | tiene `perm:product-inventory-query:product_overviews:read` |
| `inventario.test` | Sí | `422` | tiene `perm:product-inventory-query:product_overviews:read` |
| `reportes.test` | No | `403` | no tiene `perm:product-inventory-query:product_overviews:read` |
| `consulta.test` | No | `403` | no tiene `perm:product-inventory-query:product_overviews:read` |

Respuesta sin permiso (`403`), que no revela el permiso exigido:

```json
{
  "type": "https://sio/errors/product-inventory-query/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/companies/d22a0000-0000-4000-8000-000000000001/product-overviews",
  "code": "PRODUCT_INVENTORY_QUERY.FORBIDDEN",
  "trace_id": "<asignado por el servicio>"
}
```

## Respuesta esperada

Estado `422`.

```json
{
  "type": "https://sio/errors/product-inventory-query/invalid-cursor",
  "title": "Cursor inválido",
  "status": 422,
  "detail": "El cursor no es válido. Repita la consulta sin cursor.",
  "instance": "/api/v1/companies/d22a0000-0000-4000-8000-000000000001/product-overviews",
  "code": "PRODUCT_INVENTORY_QUERY.INVALID_CURSOR",
  "trace_id": "<asignado por el servicio>"
}
```
