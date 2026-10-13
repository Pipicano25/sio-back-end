# Paso 05 de 07 — Cambiar la moneda (sin precio en el producto)

Ejercicio 1 — Adopción de productos del Excel · [← Paso anterior](04-rechazos.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](06-consultar-y-estados.md)

**Objetivo:** El producto de la empresa no admite precio ni costo (spec 019); la moneda sí se cambia.

**Necesita (de pasos anteriores):** `<CP_AGUJA>` — pasos [03](03-adoptar-aguja.md)

---

## 1. Intentar fijar un precio en el producto (rechazado)

```http
PUT /api/v1/company-products/<CP_AGUJA>
```

```json
{
  "internal_code": "000537",
  "reference_code": "71430",
  "display_name": "AGUJA 18GX1 1/2 CAJAX100 RFZC18B RYMCO",
  "short_name": "AGUJA 18GX1 1/2",
  "sale_price": "1500.50",
  "currency_code": "CLP",
  "reference_cost": "0",
  "inventory_control_enabled": true,
  "lot_tracking_enabled": true,
  "expiration_tracking_enabled": true,
  "is_purchasable": true,
  "is_sellable": true,
  "version": 1
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `company_products` solo tienen `read`; les falta `update`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- El `PUT` reemplaza todos los campos modificables y exige la `version` vigente.
- `sale_price` y `reference_cost` ya no existen (spec 019): enviarlos responde `422 VALIDATION_ERROR`, aunque sean `0`. El precio se registra en una lista, por presentación.

**Respuesta esperada (error) — `422 Unprocessable Content`** (abreviada)

```json
{
  "status": 422,
  "code": "COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR",
  "detail": "La solicitud contiene datos inválidos.",
  "errors": [
    {
      "field": "sale_price",
      "message": "Extra inputs are not permitted",
      "code": "VALIDATION_ERROR"
    },
    {
      "field": "reference_cost",
      "message": "Extra inputs are not permitted",
      "code": "VALIDATION_ERROR"
    }
  ]
}
```

## 2. Cambiar la moneda

```http
PUT /api/v1/company-products/<CP_AGUJA>
```

```json
{
  "internal_code": "000537",
  "reference_code": "71430",
  "display_name": "AGUJA 18GX1 1/2 CAJAX100 RFZC18B RYMCO",
  "short_name": "AGUJA 18GX1 1/2",
  "currency_code": "clp",
  "inventory_control_enabled": true,
  "lot_tracking_enabled": true,
  "expiration_tracking_enabled": true,
  "is_purchasable": true,
  "is_sellable": true,
  "version": 1
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `company_products` solo tienen `read`; les falta `update`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- `clp` se normaliza a `CLP`; la moneda elige la lista de precios predeterminada.
- El `PUT` no consulta Product Catalog y la versión sube a 2.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "id": "<CP_AGUJA>",
  "currency_code": "CLP",
  "version": 2
}
```

---

[← Paso anterior](04-rechazos.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](06-consultar-y-estados.md)
