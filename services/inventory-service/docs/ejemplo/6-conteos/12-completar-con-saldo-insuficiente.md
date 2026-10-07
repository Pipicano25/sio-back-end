# Paso 12. Completar el segundo conteo

Ejercicio 6: Conteos físicos.

## Llamada

`POST /api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-counts/<CONTEO_2>/complete`

Ejecuta: `inventario.test`.

### Solicitud

```json
{
  "completion_key": "d44f0600-0000-4000-8000-000000000002",
  "version": 2
}
```

### Por qué

- La diferencia registrada (−8) se aplica sobre el saldo vigente (3): quedaría negativo. Se rechaza con `INSUFFICIENT_STOCK` y `shortages`; no se aplica nada y el conteo sigue en curso.

## Permiso

La URL exige `perm:inventory:counts:create`.

Además exige un **usuario humano** (una cuenta de servicio recibe `403` aunque tenga el permiso por comodín), miembro `ACTIVE` de la empresa y, en ajustes y conteos, con asignación `ACTIVE` a la sucursal (lo resuelve Operational Context con el token del usuario). Los usuarios con el permiso no repiten la llamada en este ejercicio porque cambiaría su estado.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `—` | tiene `perm:all:all:all`; no se repite (cambiaría el estado) |
| `supervisor.test` | Sí | `—` | tiene `perm:all:all:create`; no se repite (cambiaría el estado) |
| `compras.test` | No | `403` | no tiene `perm:inventory:counts:create` |
| `ventas.test` | No | `403` | no tiene `perm:inventory:counts:create` |
| `inventario.test` | Sí | `409` | tiene `perm:inventory:counts:create` |
| `reportes.test` | No | `403` | no tiene `perm:inventory:counts:create` |
| `consulta.test` | No | `403` | no tiene `perm:inventory:counts:create` |

Respuesta sin permiso (`403`), que no revela el permiso exigido:

```json
{
  "type": "https://sio/errors/inventory/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-counts/<CONTEO_2>/complete",
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
  "instance": "/api/v1/companies/d44a0000-0000-4000-8000-000000000001/inventory-counts/<CONTEO_2>/complete",
  "code": "INVENTORY.INSUFFICIENT_STOCK",
  "trace_id": "<asignado por Inventory>",
  "shortages": [
    {
      "index": 0,
      "company_product_id": "d44d0000-0000-4000-8000-000000000001",
      "available": "3.0000",
      "requested": "8.0000"
    }
  ]
}
```
