# Paso 3. Salida con una línea sin saldo suficiente

Ejercicio 2: Salidas de venta.

## Llamada

`POST /api/v1/inventory-outputs`

Ejecuta: `inventory-test-operator` (cuenta de servicio).

### Solicitud

```json
{
  "operation_key": "d44f0100-0000-4000-8000-000000000003",
  "company_id": "d44a0000-0000-4000-8000-000000000001",
  "branch_id": "d44b0000-0000-4000-8000-000000000001",
  "origin_type": "SALE",
  "origin_id": "d44e0000-0000-4000-8000-000000000002",
  "application_user_id": "d44c0000-0000-4000-8000-000000000001",
  "correlation_id": "d44f0200-0000-4000-8000-000000000003",
  "reason": null,
  "lines": [
    {
      "origin_detail_id": "d44f0300-0000-4000-8000-000000000003",
      "company_product_id": "d44d0000-0000-4000-8000-000000000001",
      "quantity": "2"
    },
    {
      "origin_detail_id": "d44f0300-0000-4000-8000-000000000004",
      "company_product_id": "d44d0000-0000-4000-8000-000000000002",
      "quantity": "1"
    }
  ]
}
```

### Por qué

- El aceite no tiene saldo: la operación completa se rechaza y el arroz tampoco se descuenta.
- `shortages` indica cada línea afectada con lo disponible y lo pedido.
- El saldo nunca queda negativo, tampoco con ventas simultáneas.

## Permiso

La URL exige `perm:inventory:outputs:create`.

Además exige que el token sea de una **cuenta de servicio**: un usuario humano recibe `403` aunque tenga el permiso por comodín. Solo puede ejecutarla `inventory-test-operator` (o el cliente técnico de Purchase o Sales con el mismo permiso).

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | No | `403` | tiene `perm:all:all:all` por comodín, pero no es una cuenta de servicio |
| `supervisor.test` | No | `403` | tiene `perm:all:all:create` por comodín, pero no es una cuenta de servicio |
| `compras.test` | No | `403` | no tiene `perm:inventory:outputs:create` y no es una cuenta de servicio |
| `ventas.test` | No | `403` | no tiene `perm:inventory:outputs:create` y no es una cuenta de servicio |
| `inventario.test` | No | `403` | no tiene `perm:inventory:outputs:create` y no es una cuenta de servicio |
| `reportes.test` | No | `403` | no tiene `perm:inventory:outputs:create` y no es una cuenta de servicio |
| `consulta.test` | No | `403` | no tiene `perm:inventory:outputs:create` y no es una cuenta de servicio |

Respuesta sin permiso (`403`), que no revela el permiso exigido:

```json
{
  "type": "https://sio/errors/inventory/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/inventory-outputs",
  "code": "INVENTORY.FORBIDDEN",
  "trace_id": "<asignado por Inventory>"
}
```

## Respuesta esperada

Estado `409`.

```json
{
  "type": "https://sio/errors/inventory/insufficient-stock",
  "title": "Saldo insuficiente",
  "status": 409,
  "detail": "No hay saldo suficiente para aplicar la operación; no se aplicó ninguna línea.",
  "instance": "/api/v1/inventory-outputs",
  "code": "INVENTORY.INSUFFICIENT_STOCK",
  "trace_id": "<asignado por Inventory>",
  "shortages": [
    {
      "index": 1,
      "company_product_id": "d44d0000-0000-4000-8000-000000000002",
      "available": "0.0000",
      "requested": "1.0000"
    }
  ]
}
```
