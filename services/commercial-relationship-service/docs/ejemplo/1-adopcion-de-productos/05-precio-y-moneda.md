# Paso 05 de 07 — Cambiar precio y moneda

Ejercicio 1 — Adopción de productos del Excel · [← Paso anterior](04-rechazos.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](06-consultar-y-estados.md)

**Objetivo:** Mostrar los decimales de cada moneda (precio **ficticio**).

**Necesita (de pasos anteriores):** `<CP_AGUJA>` — pasos [03](03-adoptar-aguja.md)

---

## 1. Fijar un precio en pesos chilenos con decimales (rechazado)

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
- `CLP` no usa decimales (ISO 4217): `1500.50` → `422 PRICE_SCALE_NOT_ALLOWED`, sin redondear.

**Respuesta esperada (error) — `422 Unprocessable Content`** (abreviada)

```json
{
  "status": 422,
  "code": "COMMERCIAL_RELATIONSHIP.PRICE_SCALE_NOT_ALLOWED",
  "detail": "El precio admite como máximo 0 decimales en CLP.",
  "errors": [
    {
      "field": "sale_price",
      "message": "El precio admite como máximo 0 decimales en CLP.",
      "code": "PRICE_SCALE_NOT_ALLOWED"
    }
  ]
}
```

## 2. Fijar el precio sin decimales

```http
PUT /api/v1/company-products/<CP_AGUJA>
```

```json
{
  "internal_code": "000537",
  "reference_code": "71430",
  "display_name": "AGUJA 18GX1 1/2 CAJAX100 RFZC18B RYMCO",
  "short_name": "AGUJA 18GX1 1/2",
  "sale_price": "1500",
  "currency_code": "clp",
  "reference_cost": "820.5",
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

- `clp` se normaliza a `CLP`. El precio se devuelve como `"1500.00"` (escala de la columna) y el costo de referencia con 4 decimales (`"820.5000"`).
- El `PUT` no consulta Product Catalog y la versión sube a 2.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "id": "<CP_AGUJA>",
  "sale_price": "1500.00",
  "currency_code": "CLP",
  "reference_cost": "820.5000",
  "version": 2
}
```

---

[← Paso anterior](04-rechazos.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](06-consultar-y-estados.md)
