# Paso 3. Filtro de mínimos sin el permiso

Ejercicio 6: Permisos y bloques visibles.

## Llamada

`GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/inventory-overviews?minimum_state=BELOW_MINIMUM`

Ejecuta: `ventas.test`.

### Por qué

- `minimum_state` depende del bloque de mínimos, que `ventas.test` no puede ver: `403`.
- Quien sí tiene `perm:inventory:product-policies:read` (`inventario`, `supervisor`, `admin`) obtiene `200`.

## Permiso

La URL exige `perm:product-inventory-query:inventory_overviews:read`.

Además exige `perm:inventory:product-policies:read`.

Además, el usuario debe ser miembro `ACTIVE` de la empresa (lo verifica Operational Context con su token antes de cualquier otra consulta). No se exige asignación a la sucursal.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `200` | tiene `perm:all:all:all`, `perm:all:all:all` |
| `supervisor.test` | Sí | `200` | tiene `perm:all:all:read`, `perm:all:all:read` |
| `compras.test` | No | `403` | no tiene `perm:product-inventory-query:inventory_overviews:read` |
| `ventas.test` | No | `403` | tiene `perm:product-inventory-query:inventory_overviews:read`, pero no `perm:inventory:product-policies:read` |
| `inventario.test` | Sí | `200` | tiene `perm:product-inventory-query:inventory_overviews:read`, `perm:inventory:product-policies:read` |
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

Estado `403`.

```json
{
  "type": "https://sio/errors/product-inventory-query/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "No tiene permiso para usar este filtro.",
  "instance": "/api/v1/companies/d22a0000-0000-4000-8000-000000000001/inventory-overviews",
  "code": "PRODUCT_INVENTORY_QUERY.FORBIDDEN",
  "trace_id": "<asignado por el servicio>"
}
```
