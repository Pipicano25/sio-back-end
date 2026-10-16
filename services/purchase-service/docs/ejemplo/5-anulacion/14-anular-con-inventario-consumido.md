# Paso 14. Anular cuando sus unidades ya se vendieron

Ejercicio 5: Anulación.

## Llamada

`POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<VENDIDA>/cancellation`

Ejecuta: `compras.test`.

Cabeceras: `Idempotency-Key: anular-0009`.

Situación simulada antes de la llamada: `consume:ENTRADA_VENDIDA` (en la prueba automática, sobre el doble de Inventory).

### Solicitud

```json
{
  "version": "<VERSION_VENDIDA_RECIBIDA>",
  "reason": "Error de precio"
}
```

### Por qué

- Inventory responde `ENTRY_LAYER_CONSUMED`: la compra sigue `CONFIRMED`.
- Primero se anulan las ventas que consumieron las unidades, o se registra un ajuste.

## Permiso

La URL exige `perm:purchase:purchases:delete`.

Además exige un **usuario humano** (una cuenta de servicio recibe `403` aunque tenga el permiso por comodín), miembro `ACTIVE` de la empresa y, en compras, hitos, confirmación y anulación, con asignación `ACTIVE` a la sucursal de la compra (lo resuelve Operational Context con el token del usuario). Los usuarios con el permiso no repiten la llamada porque cambiaría el estado del ejercicio.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `—` | tiene `perm:all:all:all` y asignación a la sucursal; no se repite (cambiaría el estado) |
| `supervisor.test` | No | `403` | no tiene `perm:purchase:purchases:delete` |
| `compras.test` | Sí | `409` | tiene `perm:purchase:purchases:delete` y asignación a la sucursal |
| `ventas.test` | No | `403` | no tiene `perm:purchase:purchases:delete` |
| `inventario.test` | No | `403` | no tiene `perm:purchase:purchases:delete` |
| `reportes.test` | No | `403` | no tiene `perm:purchase:purchases:delete` |
| `consulta.test` | No | `403` | no tiene `perm:purchase:purchases:delete` |

Respuesta sin permiso (`403`), que no revela el permiso exigido:

```json
{
  "type": "https://sio/errors/purchase/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<VENDIDA>/cancellation",
  "code": "PURCHASE.FORBIDDEN",
  "trace_id": "<asignado por el servicio>"
}
```

## Respuesta esperada

Estado `409`.

```json
{
  "type": "https://sio/errors/purchase/inventory-already-consumed",
  "title": "Inventario ya consumido",
  "status": 409,
  "detail": "La compra no se puede anular porque sus unidades ya fueron consumidas en Inventory. Anule antes las ventas que las consumieron o solicite un ajuste.",
  "instance": "/api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<VENDIDA>/cancellation",
  "code": "PURCHASE.INVENTORY_ALREADY_CONSUMED",
  "trace_id": "<asignado por el servicio>"
}
```
