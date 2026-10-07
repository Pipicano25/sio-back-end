# Paso 7. Inactivar la política del arroz

Ejercicio 8: Políticas de inventario.

## Llamada

`POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-policies/<POLITICA>/deactivate`

Ejecuta: `admin.test`.

### Solicitud

```json
{
  "version": 1
}
```

### Por qué

- No se elimina: queda inactiva y se puede crear otra.

## Permiso

La URL exige `perm:inventory:product-policies:update`.

Además exige un **usuario humano** (una cuenta de servicio recibe `403` aunque tenga el permiso por comodín), miembro `ACTIVE` de la empresa y, en ajustes y conteos, con asignación `ACTIVE` a la sucursal (lo resuelve Operational Context con el token del usuario). Los usuarios con el permiso no repiten la llamada en este ejercicio porque cambiaría su estado.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `200` | tiene `perm:all:all:all` |
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
  "instance": "/api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-policies/<POLITICA>/deactivate",
  "code": "INVENTORY.FORBIDDEN",
  "trace_id": "<asignado por Inventory>"
}
```

## Respuesta esperada

Estado `200`.

```json
{
  "id": "<POLITICA>",
  "company_id": "d44a0000-0000-4000-8000-000000000001",
  "branch_id": "d44b0000-0000-4000-8000-000000000001",
  "company_product_id": "d44d0000-0000-4000-8000-000000000001",
  "minimum_stock": "5.0000",
  "target_stock": "20.0000",
  "service_level": "0.9500",
  "safety_stock_method": "BASIC",
  "calculation_window_days": 90,
  "replenishment_mode": "MANUAL",
  "auto_purchase_enabled": false,
  "is_active": false,
  "version": 2,
  "created_at": "<asignado por Inventory>",
  "created_by": "admin.test",
  "updated_at": "<asignado por Inventory>",
  "updated_by": "admin.test"
}
```
