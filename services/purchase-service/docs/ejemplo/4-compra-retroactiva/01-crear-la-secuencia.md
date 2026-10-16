# Paso 1. Crear la secuencia mensual de la empresa

Ejercicio 4: Compra retroactiva.

## Llamada

`POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchase-sequences`

Ejecuta: `compras.test`.

### Solicitud

```json
{
  "series_code": "PRINCIPAL",
  "prefix": "CP",
  "separator": "-",
  "initial_number": 1,
  "number_length": 6,
  "reset_policy": "MONTHLY"
}
```

### Por qué

- Sin una secuencia activa ninguna compra puede confirmarse.
- `MONTHLY` lleva un contador independiente por año-mes de la fecha de la compra.

## Permiso

La URL exige `perm:purchase:purchase_sequences:create`.

Además exige un **usuario humano** (una cuenta de servicio recibe `403` aunque tenga el permiso por comodín), miembro `ACTIVE` de la empresa y, en compras, hitos, confirmación y anulación, con asignación `ACTIVE` a la sucursal de la compra (lo resuelve Operational Context con el token del usuario). Los usuarios con el permiso no repiten la llamada porque cambiaría el estado del ejercicio.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `—` | tiene `perm:all:all:all` y asignación a la sucursal; no se repite (cambiaría el estado) |
| `supervisor.test` | Sí | `—` | tiene `perm:all:all:create` y asignación a la sucursal; no se repite (cambiaría el estado) |
| `compras.test` | Sí | `201` | tiene `perm:purchase:purchase_sequences:create` y asignación a la sucursal |
| `ventas.test` | No | `403` | no tiene `perm:purchase:purchase_sequences:create` |
| `inventario.test` | No | `403` | no tiene `perm:purchase:purchase_sequences:create` |
| `reportes.test` | No | `403` | no tiene `perm:purchase:purchase_sequences:create` |
| `consulta.test` | No | `403` | no tiene `perm:purchase:purchase_sequences:create` |

Respuesta sin permiso (`403`), que no revela el permiso exigido:

```json
{
  "type": "https://sio/errors/purchase/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchase-sequences",
  "code": "PURCHASE.FORBIDDEN",
  "trace_id": "<asignado por el servicio>"
}
```

## Respuesta esperada

Estado `201`.

```json
{
  "id": "<SECUENCIA>",
  "company_id": "d14a0000-0000-4000-8000-000000000001",
  "branch_id": null,
  "document_kind": "PURCHASE",
  "series_code": "PRINCIPAL",
  "prefix": "CP",
  "separator": "-",
  "initial_number": 1,
  "maximum_number": null,
  "number_length": 6,
  "reset_policy": "MONTHLY",
  "is_active": true,
  "version": 1,
  "created_at": "<asignado por el servicio>",
  "updated_at": "<asignado por el servicio>",
  "created_by": "compras.test",
  "updated_by": "compras.test",
  "counters": []
}
```

## Variables que se guardan

- `<SECUENCIA>` = `id` de la respuesta.
