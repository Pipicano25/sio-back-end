# Paso 10. Registrar 0 arroces contados

Ejercicio 6: Conteos físicos.

## Llamada

`PUT /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-counts/<CONTEO_2>/details/d44d0000-0000-4000-8000-000000000001`

Ejecuta: `inventario.test`.

### Solicitud

```json
{
  "counted_quantity": "0"
}
```

### Por qué

- Diferencia −8 sobre el saldo de ese momento.

## Permiso

La URL exige `perm:inventory:counts:create`.

Además exige un **usuario humano** (una cuenta de servicio recibe `403` aunque tenga el permiso por comodín), miembro `ACTIVE` de la empresa y, en ajustes y conteos, con asignación `ACTIVE` a la sucursal (lo resuelve Operational Context con el token del usuario). Los usuarios con el permiso no repiten la llamada en este ejercicio porque cambiaría su estado.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `—` | tiene `perm:all:all:all`; no se repite (cambiaría el estado) |
| `supervisor.test` | Sí | `—` | tiene `perm:all:all:create`; no se repite (cambiaría el estado) |
| `compras.test` | No | `403` | no tiene `perm:inventory:counts:create` |
| `ventas.test` | No | `403` | no tiene `perm:inventory:counts:create` |
| `inventario.test` | Sí | `200` | tiene `perm:inventory:counts:create` |
| `reportes.test` | No | `403` | no tiene `perm:inventory:counts:create` |
| `consulta.test` | No | `403` | no tiene `perm:inventory:counts:create` |

Respuesta sin permiso (`403`), que no revela el permiso exigido:

```json
{
  "type": "https://sio/errors/inventory/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-counts/<CONTEO_2>/details/d44d0000-0000-4000-8000-000000000001",
  "code": "INVENTORY.FORBIDDEN",
  "trace_id": "<asignado por Inventory>"
}
```

## Respuesta esperada

Estado `200`.

```json
{
  "id": "<asignado por Inventory>",
  "inventory_count_id": "<CONTEO_2>",
  "company_product_id": "d44d0000-0000-4000-8000-000000000001",
  "system_quantity_snapshot": "8.0000",
  "counted_quantity": "0.0000",
  "difference_quantity": "-8.0000",
  "unit_cost": null,
  "inventory_adjustment_id": null,
  "counted_by_user_id": "d44c0000-0000-4000-8000-000000000105",
  "counted_at": "<asignado por Inventory>"
}
```
