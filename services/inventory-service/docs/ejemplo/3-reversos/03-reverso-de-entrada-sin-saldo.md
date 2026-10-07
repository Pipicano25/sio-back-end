# Paso 3. Revertir la entrada cuando ya se vendió parte

Ejercicio 3: Reversos.

## Llamada

`POST /api/v1/inventory-entries/<OP_ENTRADA>/reversal`

Ejecuta: `inventory-test-operator` (cuenta de servicio).

### Solicitud

```json
{
  "operation_key": "d44f0100-0000-4000-8000-000000000003",
  "company_id": "d44a0000-0000-4000-8000-000000000001",
  "application_user_id": "d44c0000-0000-4000-8000-000000000001",
  "correlation_id": "d44f0200-0000-4000-8000-000000000003",
  "reason": "Anulación de la compra ficticia"
}
```

### Por qué

- La capa de la entrada ya entregó 4 unidades a la venta: se rechaza con `ENTRY_LAYER_CONSUMED` sin cambios (013, DS-16).
- La corrección es anular antes la venta (paso 4) o registrar un ajuste.

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
  "instance": "/api/v1/inventory-entries/<OP_ENTRADA>/reversal",
  "code": "INVENTORY.FORBIDDEN",
  "trace_id": "<asignado por Inventory>"
}
```

## Respuesta esperada

Estado `409`.

```json
{
  "type": "https://sio/errors/inventory/entry-layer-consumed",
  "title": "Capa de la entrada consumida",
  "status": 409,
  "detail": "La entrada no se puede revertir porque sus unidades ya fueron consumidas. Anule antes las ventas que las consumieron o registre un ajuste.",
  "instance": "/api/v1/inventory-entries/<OP_ENTRADA>/reversal",
  "code": "INVENTORY.ENTRY_LAYER_CONSUMED",
  "trace_id": "<asignado por Inventory>"
}
```
