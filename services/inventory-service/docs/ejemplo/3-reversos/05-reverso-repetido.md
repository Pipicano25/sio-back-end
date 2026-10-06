# Paso 5. Revertir otra vez la misma salida con otra clave

Ejercicio 3: Reversos.

## Llamada

`POST /api/v1/inventory-outputs/<OP_SALIDA>/reversal`

Ejecuta: `inventory-test-operator` (cuenta de servicio).

### Solicitud

```json
{
  "operation_key": "d44f0100-0000-4000-8000-000000000005",
  "company_id": "d44a0000-0000-4000-8000-000000000001",
  "application_user_id": "d44c0000-0000-4000-8000-000000000001",
  "correlation_id": "d44f0200-0000-4000-8000-000000000005",
  "reason": "Segundo intento de anulación"
}
```

### Por qué

- Una operación se revierte a lo sumo una vez (`ALREADY_REVERSED`).

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
  "instance": "/api/v1/inventory-outputs/<OP_SALIDA>/reversal",
  "code": "INVENTORY.FORBIDDEN",
  "trace_id": "<asignado por Inventory>"
}
```

## Respuesta esperada

Estado `409`.

```json
{
  "type": "https://sio/errors/inventory/already-reversed",
  "title": "Operación ya revertida",
  "status": 409,
  "detail": "La operación ya fue revertida.",
  "instance": "/api/v1/inventory-outputs/<OP_SALIDA>/reversal",
  "code": "INVENTORY.ALREADY_REVERSED",
  "trace_id": "<asignado por Inventory>"
}
```
