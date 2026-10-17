# Paso 11. Productos bajo el mínimo en la sucursal (spec 022)

Ejercicio 8: Políticas de inventario.

## Llamada

`POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-product-sets`

Ejecuta: `inventario.test`.

### Solicitud

```json
{
  "branch_ids": [
    "d44b0000-0000-4000-8000-000000000001"
  ],
  "minimum_state": "BELOW_MINIMUM",
  "unit": "PAIRS",
  "limit": 20
}
```

### Por qué

- El arroz no tiene saldo en este ejercicio: cuenta con 0 y queda bajo su mínimo de 5 (faltante 5).
- Los pares van por faltante descendente; cada uno trae su `position` para continuar con `after`.
- No hay conteos ni costos: `has_more` dice si quedan pares.

## Permiso

La URL exige `perm:inventory:balances:read`.

Además, el usuario debe ser miembro `ACTIVE` de la empresa y tener `perm:operational-context:application_users:read` (lo exige Operational Context al resolver su acceso). No se exige asignación a la sucursal.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `200` | tiene `perm:all:all:all` |
| `supervisor.test` | Sí | `200` | tiene `perm:all:all:read` |
| `compras.test` | No | `403` | no tiene `perm:inventory:balances:read` |
| `ventas.test` | No | `403` | no tiene `perm:inventory:balances:read` |
| `inventario.test` | Sí | `200` | tiene `perm:inventory:balances:read` |
| `reportes.test` | No | `403` | no tiene `perm:inventory:balances:read` |
| `consulta.test` | No | `403` | no tiene `perm:inventory:balances:read` |

Respuesta sin permiso (`403`), que no revela el permiso exigido:

```json
{
  "type": "https://sio/errors/inventory/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-product-sets",
  "code": "INVENTORY.FORBIDDEN",
  "trace_id": "<asignado por Inventory>"
}
```

## Respuesta esperada

Estado `200`.

```json
{
  "items": [
    {
      "company_product_id": "d44d0000-0000-4000-8000-000000000001",
      "branch_id": "d44b0000-0000-4000-8000-000000000001",
      "base_quantity": "0.0000",
      "minimum_stock": "5.0000",
      "shortfall": "5.0000",
      "position": {
        "k": [
          "5.0000"
        ],
        "id": "<asignado por Inventory>",
        "branch_id": "d44b0000-0000-4000-8000-000000000001"
      }
    }
  ],
  "has_more": false
}
```
