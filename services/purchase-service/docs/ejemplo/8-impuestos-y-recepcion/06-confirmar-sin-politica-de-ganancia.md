# Paso 6. Confirmar con una presentación sin política de ganancia

Ejercicio 8: Impuesto de compra por tasa.

## Llamada

`POST /api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/confirmation`

Ejecuta: `compras.test`.

Cabeceras: `Idempotency-Key: impuestos-0001`.

Situación simulada antes de la llamada: `sin_politica:aceite` (en la prueba automática, sobre el doble de Inventory).

### Solicitud

```json
{
  "version": 2
}
```

### Por qué

- Spec 021 (FR-021-35): cada presentación debe tener una política de ganancia activa (0 % cuenta) en una lista activa, vigente y de la moneda de la compra. El aceite no la tiene: `409 PRICING_POLICY_NOT_CONFIGURED` con la línea en `errors[]`; la compra sigue en `DRAFT`, sin número ni operación, y la clave no se consume.
- Basta una lista que la cubra; las demás pueden seguir siendo manuales. Al configurarla en Commercial Relationship, la misma confirmación continúa con las demás reglas. Purchase solo sabe si hay cobertura: no ve porcentajes ni costos.

## Permiso

La URL exige `perm:purchase:purchases:update`.

Además exige un **usuario humano** (una cuenta de servicio recibe `403` aunque tenga el permiso por comodín), miembro `ACTIVE` de la empresa y, en compras, hitos, confirmación y anulación, con asignación `ACTIVE` a la sucursal de la compra (lo resuelve Operational Context con el token del usuario). Los usuarios con el permiso no repiten la llamada porque cambiaría el estado del ejercicio.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `—` | tiene `perm:all:all:all` y asignación a la sucursal; no se repite (cambiaría el estado) |
| `supervisor.test` | Sí | `—` | tiene `perm:all:all:update` y asignación a la sucursal; no se repite (cambiaría el estado) |
| `compras.test` | Sí | `409` | tiene `perm:purchase:purchases:update` y asignación a la sucursal |
| `ventas.test` | No | `403` | no tiene `perm:purchase:purchases:update` |
| `inventario.test` | No | `403` | no tiene `perm:purchase:purchases:update` |
| `reportes.test` | No | `403` | no tiene `perm:purchase:purchases:update` |
| `consulta.test` | No | `403` | no tiene `perm:purchase:purchases:update` |

Respuesta sin permiso (`403`), que no revela el permiso exigido:

```json
{
  "type": "https://sio/errors/purchase/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/confirmation",
  "code": "PURCHASE.FORBIDDEN",
  "trace_id": "<asignado por el servicio>"
}
```

## Respuesta esperada

Estado `409`.

```json
{
  "type": "https://sio/errors/purchase/pricing-policy-not-configured",
  "title": "Política de ganancia sin configurar",
  "status": 409,
  "detail": "Una o más presentaciones no tienen una política de ganancia aplicable en una lista activa y vigente de la moneda de la compra: configúrela en Commercial Relationship antes de confirmar.",
  "instance": "/api/v1/companies/d14a0000-0000-4000-8000-000000000001/purchases/<COMPRA>/confirmation",
  "code": "PURCHASE.PRICING_POLICY_NOT_CONFIGURED",
  "trace_id": "<asignado por el servicio>",
  "errors": [
    {
      "field": "lines[1].company_product_presentation_id",
      "message": "La presentación no tiene una política de ganancia aplicable en una lista activa y vigente de la moneda.",
      "code": "PRICING_POLICY_NOT_CONFIGURED",
      "line_number": 2,
      "company_product_presentation_id": "0e2be67b-ba11-51b8-9dd7-04739ec7d8d4"
    }
  ]
}
```
