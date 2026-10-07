# Paso 4. Ajuste positivo de un producto sin capas, sin costo

Ejercicio 5: Ajustes de inventario.

## Llamada

`POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-adjustments`

Ejecuta: `inventario.test`.

### Solicitud

```json
{
  "adjustment_key": "d44f0500-0000-4000-8000-000000000003",
  "branch_id": "d44b0000-0000-4000-8000-000000000001",
  "company_product_id": "d44d0000-0000-4000-8000-000000000002",
  "adjustment_type": "POSITIVE",
  "quantity": "4",
  "unit_cost": null,
  "reason": "Inventario inicial encontrado"
}
```

### Por qué

- El aceite nunca tuvo capas en la sucursal: no hay costo conocido y `unit_cost` es obligatorio (`UNIT_COST_REQUIRED`). Ninguna cantidad entra sin costo.

## Permiso

La URL exige `perm:inventory:adjustments:create`.

Además exige un **usuario humano** (una cuenta de servicio recibe `403` aunque tenga el permiso por comodín), miembro `ACTIVE` de la empresa y, en ajustes y conteos, con asignación `ACTIVE` a la sucursal (lo resuelve Operational Context con el token del usuario). Los usuarios con el permiso no repiten la llamada en este ejercicio porque cambiaría su estado.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `—` | tiene `perm:all:all:all`; no se repite (cambiaría el estado) |
| `supervisor.test` | Sí | `—` | tiene `perm:all:all:create`; no se repite (cambiaría el estado) |
| `compras.test` | No | `403` | no tiene `perm:inventory:adjustments:create` |
| `ventas.test` | No | `403` | no tiene `perm:inventory:adjustments:create` |
| `inventario.test` | Sí | `422` | tiene `perm:inventory:adjustments:create` |
| `reportes.test` | No | `403` | no tiene `perm:inventory:adjustments:create` |
| `consulta.test` | No | `403` | no tiene `perm:inventory:adjustments:create` |

Respuesta sin permiso (`403`), que no revela el permiso exigido:

```json
{
  "type": "https://sio/errors/inventory/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-adjustments",
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
  "instance": "/api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-adjustments",
  "code": "INVENTORY.VALIDATION_ERROR",
  "trace_id": "<asignado por Inventory>",
  "errors": [
    {
      "field": "unit_cost",
      "message": "No hay un costo conocido para el producto en la sucursal: informe el costo unitario.",
      "code": "UNIT_COST_REQUIRED"
    }
  ]
}
```
