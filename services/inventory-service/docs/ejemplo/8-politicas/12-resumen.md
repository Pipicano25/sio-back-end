# Paso 12. Indicadores de la sucursal (spec 022)

Ejercicio 8: Políticas de inventario.

## Llamada

`POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-summary`

Ejecuta: `inventario.test`.

### Solicitud

```json
{
  "branch_ids": [
    "d44b0000-0000-4000-8000-000000000001"
  ]
}
```

### Por qué

- Inventory calcula los indicadores en una consulta agregada: saldos positivos, saldos registrados en cero (un producto sin registro de saldo no cuenta), políticas activas y productos bajo mínimo.
- Sin `include_valuation` no se informa el valor del inventario.

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
  "instance": "/api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-summary",
  "code": "INVENTORY.FORBIDDEN",
  "trace_id": "<asignado por Inventory>"
}
```

## Respuesta esperada

Estado `200`.

```json
{
  "branches": [
    {
      "products_with_positive_balance": 0,
      "products_with_zero_balance": 0,
      "products_with_policy": 1,
      "products_below_minimum": 1,
      "branch_id": "d44b0000-0000-4000-8000-000000000001"
    }
  ],
  "consolidated": {
    "products_with_positive_balance": 0,
    "products_with_zero_balance": 0,
    "products_with_policy": 1,
    "products_below_minimum": 1
  }
}
```
