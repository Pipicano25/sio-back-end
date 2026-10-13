# Paso 02 de 05 — Adoptar los productos

Ejercicio 6 — Listas de precios y precio aplicable · [← Paso anterior](01-consultar-datos.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](03-lista-y-precio.md)

**Objetivo:** Crear los productos empresariales.

**Necesita (de pasos anteriores):** `<EMPRESA>`, `<GP_IRBESARTAN>`, `<GP_ACETAMINOFEN>`, `<GPRES_IRBE>`, `<GPRES_ACETA>` — pasos [01](01-consultar-datos.md)

**Deja guardado para los siguientes pasos:** `<IRBESARTAN>`, `<ACETAMINOFEN>`, `<PRES_IRBE>`, `<PRES_ACETA>`

---

## 1. Adoptar el irbesartán (fila 16577)

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

- Ejercicio 1. El producto de la empresa no tiene precio ni costo (spec 019).

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<IRBESARTAN>",
  "internal_code": "022315",
  "currency_code": "COP"
}
```

**Guardar:** `id` → `<IRBESARTAN>`

## 2. Adoptar el acetaminofén

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

- Sin precio en el producto: si no se registra un precio para su presentación, no tendrá precio.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<ACETAMINOFEN>",
  "internal_code": "000045",
  "currency_code": "COP"
}
```

**Guardar:** `id` → `<ACETAMINOFEN>`

## 3. Adoptar la caja x30 del irbesartán

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

- Ejercicio 4. Es la presentación que se vende y a la que pertenece el precio.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<PRES_IRBE>",
  "is_sellable": true,
  "status": "ACTIVE"
}
```

**Guardar:** `id` → `<PRES_IRBE>`

## 4. Adoptar la caja x100 del acetaminofén

```http
POST /api/v1/companies/<EMPRESA>/company-product-presentations
```

```json
{
  "company_product_id": "<ACETAMINOFEN>",
  "global_product_presentation_id": "<GPRES_ACETA>"
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_product_presentations:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `company_product_presentations` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `company_product_presentations` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- Queda asociada a la empresa, pero sin precio vigente no se puede vender (spec 019).

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<PRES_ACETA>",
  "is_sellable": true,
  "status": "ACTIVE"
}
```

**Guardar:** `id` → `<PRES_ACETA>`

---

[← Paso anterior](01-consultar-datos.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](03-lista-y-precio.md)
