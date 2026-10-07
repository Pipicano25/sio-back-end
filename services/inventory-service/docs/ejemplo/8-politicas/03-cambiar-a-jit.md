# Paso 3. Cambiar la estrategia de reposición

Ejercicio 8: Políticas de inventario.

## Llamada

`PUT /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-policy`

Ejecuta: `admin.test`.

### Solicitud

```json
{
  "inventory_system": "PERPETUAL",
  "valuation_method": "FIFO",
  "replenishment_strategy": "JIT",
  "version": 1
}
```

### Por qué

- Exige la `version` vigente; una versión vieja responde `409 VERSION_CONFLICT`.

## Permiso

La URL exige `perm:inventory:company-policies:update`.

Además exige un **usuario humano** (una cuenta de servicio recibe `403` aunque tenga el permiso por comodín), miembro `ACTIVE` de la empresa y, en ajustes y conteos, con asignación `ACTIVE` a la sucursal (lo resuelve Operational Context con el token del usuario). Los usuarios con el permiso no repiten la llamada en este ejercicio porque cambiaría su estado.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `200` | tiene `perm:all:all:all` |
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

Estado `200`.

```json
{
  "id": "<asignado por Inventory>",
  "company_id": "d44a0000-0000-4000-8000-000000000001",
  "inventory_system": "PERPETUAL",
  "valuation_method": "FIFO",
  "replenishment_strategy": "JIT",
  "is_active": true,
  "version": 2,
  "registered": true,
  "created_at": "<asignado por Inventory>",
  "created_by": "admin.test",
  "updated_at": "<asignado por Inventory>",
  "updated_by": "admin.test"
}
```
