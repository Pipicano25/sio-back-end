# Paso 2. Consultar la disponibilidad

Ejercicio 3: Disponibilidad antes de confirmar.

## Llamada

`GET /api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/availability`

Ejecuta: `ventas.test`.

### Por qué

- El arroz requiere 26 y hay 20 en la sucursal: `is_available = false`; el aceite alcanza.
- Es informativa: confirmar sigue validándose contra Inventory, que es la barrera real.

## Permiso

La URL exige `perm:sales:sales:read`.

Además, el usuario debe ser miembro `ACTIVE` de la empresa (Operational Context, con su token). No se exige asignación a la sucursal.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `200` | tiene `perm:all:all:all` |
| `supervisor.test` | Sí | `200` | tiene `perm:all:all:read` |
| `compras.test` | No | `403` | no tiene `perm:sales:sales:read` |
| `ventas.test` | Sí | `200` | tiene `perm:sales:all:read` |
| `inventario.test` | No | `403` | no tiene `perm:sales:sales:read` |
| `reportes.test` | Sí | `200` | tiene `perm:sales:sales:read` |
| `consulta.test` | Sí | `200` | tiene `perm:sales:sales:read` |

Respuesta sin permiso (`403`), que no revela el permiso exigido:

```json
{
  "type": "https://sio/errors/sales/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/companies/d15a0000-0000-4000-8000-000000000001/sales/<VENTA>/availability",
  "code": "SALES.FORBIDDEN",
  "trace_id": "<asignado por el servicio>"
}
```

## Respuesta esperada

Estado `200`.

```json
{
  "sale_id": "<VENTA>",
  "branch_id": "d15b0000-0000-4000-8000-000000000001",
  "all_available": false,
  "products": [
    {
      "company_product_id": "d15d0000-0000-4000-8000-000000000001",
      "line_numbers": [
        1,
        2
      ],
      "required_base_quantity": "26.0000",
      "available_base_quantity": "20.0000",
      "is_available": false
    },
    {
      "company_product_id": "d15d0000-0000-4000-8000-000000000002",
      "line_numbers": [
        3
      ],
      "required_base_quantity": "1.0000",
      "available_base_quantity": "1000.0000",
      "is_available": true
    }
  ]
}
```
