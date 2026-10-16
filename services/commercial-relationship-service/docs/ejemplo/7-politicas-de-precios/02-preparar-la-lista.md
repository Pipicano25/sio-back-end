# Paso 02 de 04 — Adoptar los productos y crear la lista

Ejercicio 7 — Políticas de ganancia de una lista de precios · [← Paso anterior](01-consultar-datos.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](03-crear-politicas.md)

**Objetivo:** Productos, presentaciones vendibles y la lista `PUBLICO`.

**Necesita (de pasos anteriores):** `<EMPRESA>`, `<GP_ACETAMINOFEN>`, `<GP_IRBESARTAN>`, `<GPRES_CAJA>`, `<GPRES_SOBRE>`, `<GPRES_IRBE>` — pasos [01](01-consultar-datos.md)

**Deja guardado para los siguientes pasos:** `<ACETAMINOFEN>`, `<IRBESARTAN>`, `<CAJA>`, `<SOBRE>`, `<IRBE>`, `<LISTA>`

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

## 2. Adoptar el irbesartán (fila 16577)

```http
POST /api/v1/companies/<EMPRESA>/company-products
```

```json
{
  "global_product_id": "<GP_IRBESARTAN>",
  "internal_code": "022315",
  "display_name": "IRBESARTAN+HIDROCLOROTIAZIDA (IRBESARTAN/HCT) 150+12.5MG TABLETA CAJAX30MK",
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
  "id": "<IRBESARTAN>",
  "internal_code": "022315"
}
```

**Guardar:** `id` → `<IRBESARTAN>`

## 3. Adoptar la caja x100 del acetaminofén

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

- Ejercicio 4. Las políticas se definen por **presentación**, la unidad que tiene precio.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<CAJA>",
  "is_sellable": true,
  "status": "ACTIVE"
}
```

**Guardar:** `id` → `<CAJA>`

## 4. Adoptar el sobre x10 del acetaminofén

```http
POST /api/v1/companies/<EMPRESA>/company-product-presentations
```

```json
{
  "company_product_id": "<ACETAMINOFEN>",
  "global_product_presentation_id": "<GPRES_SOBRE>"
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_product_presentations:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `company_product_presentations` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `company_product_presentations` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- Otra presentación del mismo producto: puede tener otra política.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<SOBRE>",
  "is_sellable": true,
  "status": "ACTIVE"
}
```

**Guardar:** `id` → `<SOBRE>`

## 5. Adoptar la caja x30 del irbesartán

```http
POST /api/v1/companies/<EMPRESA>/company-product-presentations
```

```json
{
  "company_product_id": "<IRBESARTAN>",
  "global_product_presentation_id": "<GPRES_IRBE>"
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_product_presentations:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `company_product_presentations` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `company_product_presentations` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- Ejercicio 4.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<IRBE>",
  "is_sellable": true,
  "status": "ACTIVE"
}
```

**Guardar:** `id` → `<IRBE>`

## 6. Crear la lista PUBLICO en COP

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

- Ejercicio 6. Una lista con al menos una política activa recibe precios automáticos; una lista sin políticas conserva sus precios manuales (spec 021, B-3).

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

---

[← Paso anterior](01-consultar-datos.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](03-crear-politicas.md)
