# Paso 4. Pedir promedio ponderado

Ejercicio 8: Políticas de inventario.

## Llamada

`PUT /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-policy`

Ejecuta: `admin.test`.

### Solicitud

```json
{
  "inventory_system": "PERPETUAL",
  "valuation_method": "WEIGHTED_AVERAGE",
  "replenishment_strategy": "JIT",
  "version": 2
}
```

### Por qué

- Esta fase solo valora con FIFO: `VALUATION_METHOD_NOT_SUPPORTED`.

## Permiso

La URL exige `perm:inventory:company-policies:update`.

Además exige un **usuario humano** (una cuenta de servicio recibe `403` aunque tenga el permiso por comodín), miembro `ACTIVE` de la empresa y, en ajustes y conteos, con asignación `ACTIVE` a la sucursal (lo resuelve Operational Context con el token del usuario). Los usuarios con el permiso no repiten la llamada en este ejercicio porque cambiaría su estado.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `422` | tiene `perm:all:all:all` |
| `supervisor.test` | Sí | `—` | tiene `perm:all:all:update`; no se repite (cambiaría el estado) |
| `compras.test` | No | `403` | no tiene `perm:inventory:company-policies:update` |
| `ventas.test` | No | `403` | no tiene `perm:inventory:company-policies:update` |
| `inventario.test` | No | `403` | no tiene `perm:inventory:company-policies:update` |
| `reportes.test` | No | `403` | no tiene `perm:inventory:company-policies:update` |
| `consulta.test` | No | `403` | no tiene `perm:inventory:company-policies:update` |

Respuesta sin permiso (`403`), que no revela el permiso exigido:

```json
{
  "type": "https://sio/errors/inventory/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-policy",
  "code": "INVENTORY.FORBIDDEN",
  "trace_id": "<asignado por Inventory>"
}
```

## Respuesta esperada

Estado `422`.

```json
{
  "type": "https://sio/errors/inventory/validation-error",
  "title": "Solicitud inválida",
  "status": 422,
  "detail": "La solicitud contiene datos inválidos.",
  "instance": "/api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-policy",
  "code": "INVENTORY.VALIDATION_ERROR",
  "trace_id": "<asignado por Inventory>",
  "errors": [
    {
      "field": "valuation_method",
      "message": "Esta fase solo admite la valoración FIFO (DS-11).",
      "code": "VALUATION_METHOD_NOT_SUPPORTED"
    }
  ]
}
```
