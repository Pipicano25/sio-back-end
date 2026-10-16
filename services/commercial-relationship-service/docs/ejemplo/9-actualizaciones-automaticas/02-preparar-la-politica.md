# Paso 02 de 05 — Adoptar el producto, crear la lista y la política

Ejercicio 9 — Actualizaciones automáticas de precio · [← Paso anterior](01-consultar-datos.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](03-recepciones.md)

**Objetivo:** La caja del acetaminofén en la política `Medicamentos` (30 %) de la lista `PUBLICO`.

**Necesita (de pasos anteriores):** `<EMPRESA>`, `<GP_ACETAMINOFEN>`, `<GPRES_CAJA>` — pasos [01](01-consultar-datos.md)

**Deja guardado para los siguientes pasos:** `<ACETAMINOFEN>`, `<CAJA>`, `<LISTA>`, `<MEDICAMENTOS>`

---

## 1. Adoptar el acetaminofén (fila 40)

```http
POST /api/v1/companies/<EMPRESA>/company-products
```

```json
{
  "global_product_id": "<GP_ACETAMINOFEN>",
  "internal_code": "000045",
  "display_name": "ACETAMINOFEN (ADOREM) 500MG TABLETA CAJAX100 SIEGFRIED",
  "currency_code": "COP"
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_products:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `company_products` solo tienen `read`; les falta `create`
- ℹ️ Adoptar no exige permisos en Product Catalog al usuario: la elegibilidad y el registro de primer uso los hace el servicio con su propia identidad técnica (cliente `commercial-relationship-service`).
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- Ejercicio 1.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<ACETAMINOFEN>",
  "internal_code": "000045"
}
```

**Guardar:** `id` → `<ACETAMINOFEN>`

## 2. Adoptar la caja x100 del acetaminofén

```http
POST /api/v1/companies/<EMPRESA>/company-product-presentations
```

```json
{
  "company_product_id": "<ACETAMINOFEN>",
  "global_product_presentation_id": "<GPRES_CAJA>"
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_product_presentations:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `company_product_presentations` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `company_product_presentations` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- Ejercicio 4. El precio automático es por presentación.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<CAJA>",
  "is_sellable": true,
  "status": "ACTIVE"
}
```

**Guardar:** `id` → `<CAJA>`

## 3. Crear la lista PUBLICO en COP

```http
POST /api/v1/companies/<EMPRESA>/price-lists
```

```json
{
  "code": "PUBLICO",
  "name": "Público",
  "currency_code": "COP"
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:price_lists:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `price_lists` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `price_lists` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- Ejercicio 6.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<LISTA>",
  "code": "PUBLICO",
  "currency_code": "COP",
  "status": "ACTIVE"
}
```

**Guardar:** `id` → `<LISTA>`

## 4. Crear la política Medicamentos (30 %) con la caja

```http
POST /api/v1/companies/<EMPRESA>/price-lists/<LISTA>/pricing-policies
```

```json
{
  "name": "Medicamentos",
  "markup_percentage": "30",
  "company_product_presentation_ids": [
    "<CAJA>"
  ]
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:pricing_policies:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — no tienen ningún permiso sobre `pricing_policies` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- Ejercicio 7. Desde ahora la lista `PUBLICO` recibe precios automáticos.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<MEDICAMENTOS>",
  "name": "Medicamentos",
  "markup_percentage": "30.0000",
  "presentation_count": 1
}
```

**Guardar:** `id` → `<MEDICAMENTOS>`

---

[← Paso anterior](01-consultar-datos.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](03-recepciones.md)
