# Paso 3. Reutilizar la clave con otra cantidad

Ejercicio 1: Entradas de compra.

## Llamada

`POST /api/v1/inventory-entries`

Ejecuta: `inventory-test-operator` (cuenta de servicio).

### Solicitud

```json
{
  "operation_key": "d44f0100-0000-4000-8000-000000000001",
  "company_id": "d44a0000-0000-4000-8000-000000000001",
  "branch_id": "d44b0000-0000-4000-8000-000000000001",
  "origin_type": "PURCHASE",
  "origin_id": "d44e0000-0000-4000-8000-000000000001",
  "application_user_id": "d44c0000-0000-4000-8000-000000000001",
  "correlation_id": "d44f0200-0000-4000-8000-000000000001",
  "reason": null,
  "lines": [
    {
      "origin_detail_id": "d44f0300-0000-4000-8000-000000000001",
      "company_product_id": "d44d0000-0000-4000-8000-000000000001",
      "quantity": "11",
      "unit_cost": "2500.50"
    },
    {
      "origin_detail_id": "d44f0300-0000-4000-8000-000000000002",
      "company_product_id": "d44d0000-0000-4000-8000-000000000002",
      "quantity": "5.5",
      "unit_cost": "9800"
    }
  ]
}
```

### Por qué

- La huella de la solicitud cambia: nunca se devuelve en silencio el resultado anterior.
- El consumidor debe usar una clave nueva para una solicitud nueva.

## Permiso

La URL exige `perm:inventory:entries:create`.

Además exige que el token sea de una **cuenta de servicio**: un usuario humano recibe `403` aunque tenga el permiso por comodín. Solo puede ejecutarla `inventory-test-operator` (o el cliente técnico de Purchase o Sales con el mismo permiso).

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | No | `403` | tiene `perm:all:all:all` por comodín, pero no es una cuenta de servicio |
| `supervisor.test` | No | `403` | tiene `perm:all:all:create` por comodín, pero no es una cuenta de servicio |
| `compras.test` | No | `403` | no tiene `perm:inventory:entries:create` y no es una cuenta de servicio |
| `ventas.test` | No | `403` | no tiene `perm:inventory:entries:create` y no es una cuenta de servicio |
| `inventario.test` | No | `403` | no tiene `perm:inventory:entries:create` y no es una cuenta de servicio |
| `reportes.test` | No | `403` | no tiene `perm:inventory:entries:create` y no es una cuenta de servicio |
| `consulta.test` | No | `403` | no tiene `perm:inventory:entries:create` y no es una cuenta de servicio |

Respuesta sin permiso (`403`), que no revela el permiso exigido:

```json
{
  "type": "https://sio/errors/inventory/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/inventory-entries",
  "code": "INVENTORY.FORBIDDEN",
  "trace_id": "<asignado por Inventory>"
}
```

## Respuesta esperada

Estado `409`.

```json
{
  "type": "https://sio/errors/inventory/operation-key-conflict",
  "title": "Conflicto de clave de operación",
  "status": 409,
  "detail": "La clave de operación ya se usó con una solicitud distinta. Use una clave nueva para una solicitud nueva o repita exactamente la solicitud original.",
  "instance": "/api/v1/inventory-entries",
  "code": "INVENTORY.OPERATION_KEY_CONFLICT",
  "trace_id": "<asignado por Inventory>"
}
```
