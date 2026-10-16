# Paso 03 de 03 — Configurar las tasas

Ejercicio 8 — Tasa de impuesto de compra del producto · [← Paso anterior](02-adoptar-productos.md) · [Orden del ejercicio](ORDEN.md)

**Objetivo:** Una tasa individual, un rechazo y un lote.

**Necesita (de pasos anteriores):** `<ACETAMINOFEN>`, `<EMPRESA>`, `<IRBESARTAN>` — pasos [01](01-consultar-datos.md), [02](02-adoptar-productos.md)

---

## 1. Configurar 19 % al acetaminofén (ficticio)

```http
PUT /api/v1/company-products/<ACETAMINOFEN>/purchase-tax
```

```json
{
  "version": 1,
  "purchase_tax_percentage": "19"
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_product_purchase_taxes:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — no tienen ningún permiso sobre `company_product_purchase_taxes` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- De 0 a 100 con hasta 4 decimales. Incrementa la `version` del producto y se audita como `UPDATE_COMPANY_PRODUCT_PURCHASE_TAX`.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "id": "<ACETAMINOFEN>",
  "internal_code": "000045",
  "purchase_tax_percentage": "19.0000",
  "version": 2
}
```

## 2. Dejar el acetaminofén sin configurar (rechazado)

```http
PUT /api/v1/company-products/<ACETAMINOFEN>/purchase-tax
```

```json
{
  "version": 2,
  "purchase_tax_percentage": null
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_product_purchase_taxes:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — no tienen ningún permiso sobre `company_product_purchase_taxes` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- Una tasa configurada no vuelve a `null`: `422 PURCHASE_TAX_REQUIRED`.

**Respuesta esperada (error) — `422 Unprocessable Content`** (abreviada)

```json
{
  "status": 422,
  "code": "COMMERCIAL_RELATIONSHIP.PURCHASE_TAX_REQUIRED",
  "detail": "Indique la tasa de impuesto de compra (0 es válido); no se puede dejar sin configurar.",
  "errors": [
    {
      "field": "purchase_tax_percentage",
      "message": "Indique la tasa de impuesto de compra (0 es válido); no se puede dejar sin configurar.",
      "code": "PURCHASE_TAX_REQUIRED"
    }
  ]
}
```

## 3. Configurar en lote: acetaminofén 19 % y irbesartán 0 %

```http
POST /api/v1/companies/<EMPRESA>/company-products/purchase-taxes/batch
```

```json
{
  "items": [
    {
      "company_product_id": "<ACETAMINOFEN>",
      "version": 2,
      "purchase_tax_percentage": "19"
    },
    {
      "company_product_id": "<IRBESARTAN>",
      "version": 1,
      "purchase_tax_percentage": "0"
    }
  ]
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_product_purchase_taxes:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — no tienen ningún permiso sobre `company_product_purchase_taxes` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- Hasta 100 productos, **todo o nada**: si uno falla (versión vieja, tasa inválida), no cambia ninguno. El acetaminofén ya tenía 19 %: no cambia su versión. 0 % es válido.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "internal_code": "000045",
      "purchase_tax_percentage": "19.0000",
      "version": 2
    },
    {
      "internal_code": "022315",
      "purchase_tax_percentage": "0.0000",
      "version": 2
    }
  ]
}
```

---

[← Paso anterior](02-adoptar-productos.md) · [Orden del ejercicio](ORDEN.md)
