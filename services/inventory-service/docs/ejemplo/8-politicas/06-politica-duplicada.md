# Paso 6. Otra política activa para el mismo producto

Ejercicio 8: Políticas de inventario.

## Llamada

`POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-policies`

Ejecuta: `admin.test`.

### Solicitud

```json
{
  "branch_id": "d44b0000-0000-4000-8000-000000000001",
  "company_product_id": "d44d0000-0000-4000-8000-000000000001",
  "minimum_stock": "1",
  "safety_stock_method": "BASIC",
  "replenishment_mode": "MANUAL"
}
```

### Por qué

- Una sola política activa por producto y sucursal: `ACTIVE_POLICY_EXISTS`.

## Permiso

La URL exige `perm:inventory:product-policies:update`.

Además exige un **usuario humano** (una cuenta de servicio recibe `403` aunque tenga el permiso por comodín), miembro `ACTIVE` de la empresa y, en ajustes y conteos, con asignación `ACTIVE` a la sucursal (lo resuelve Operational Context con el token del usuario). Los usuarios con el permiso no repiten la llamada en este ejercicio porque cambiaría su estado.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `409` | tiene `perm:all:all:all` |
| `supervisor.test` | Sí | `—` | tiene `perm:all:all:update`; no se repite (cambiaría el estado) |
| `compras.test` | No | `403` | no tiene `perm:inventory:product-policies:update` |
| `ventas.test` | No | `403` | no tiene `perm:inventory:product-policies:update` |
| `inventario.test` | No | `403` | no tiene `perm:inventory:product-policies:update` |
| `reportes.test` | No | `403` | no tiene `perm:inventory:product-policies:update` |
| `consulta.test` | No | `403` | no tiene `perm:inventory:product-policies:update` |

Respuesta sin permiso (`403`), que no revela el permiso exigido:

```json
{
  "type": "https://sio/errors/inventory/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-policies",
  "code": "INVENTORY.FORBIDDEN",
  "trace_id": "<asignado por Inventory>"
}
```

## Respuesta esperada

Estado `409`.

```json
{
  "type": "https://sio/errors/inventory/active-policy-exists",
  "title": "Política activa existente",
  "status": 409,
  "detail": "Ya existe una política activa para el producto en la sucursal; inactívela primero.",
  "instance": "/api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-policies",
  "code": "INVENTORY.ACTIVE_POLICY_EXISTS",
  "trace_id": "<asignado por Inventory>"
}
```
