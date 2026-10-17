# Paso 02 de 05 — Adoptar los productos y las presentaciones

Ejercicio 10 — Búsqueda progresiva de productos y presentaciones por productos · [← Paso anterior](01-consultar-datos.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](03-buscar.md)

**Objetivo:** Crear tres productos empresariales y dos presentaciones con SKU.

**Necesita (de pasos anteriores):** `<EMPRESA>`, `<GP_ACETAMINOFEN>`, `<GP_AGUJA>`, `<GP_IRBESARTAN>`, `<GPRES_CAJA>`, `<GPRES_SOBRE>` — pasos [01](01-consultar-datos.md)

**Deja guardado para los siguientes pasos:** `<ACETAMINOFEN>`, `<AGUJA>`, `<IRBESARTAN>`, `<PRES_CAJA>`, `<PRES_SOBRE>`

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

- Ejercicio 1: la adopción registra el primer uso del producto global.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<ACETAMINOFEN>",
  "internal_code": "000045",
  "display_name": "ACETAMINOFEN (ADOREM) 500MG TABLETA CAJAX100 SIEGFRIED"
}
```

**Guardar:** `id` → `<ACETAMINOFEN>`

## 2. Adoptar la aguja (fila 413)

```http
POST /api/v1/companies/<EMPRESA>/company-products
```

```json
{
  "global_product_id": "<GP_AGUJA>",
  "internal_code": "000537",
  "display_name": "AGUJA 18GX1 1/2 CAJAX100 RFZC18B RYMCO",
  "currency_code": "COP"
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_products:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `company_products` solo tienen `read`; les falta `create`
- ℹ️ Adoptar no exige permisos en Product Catalog al usuario: la elegibilidad y el registro de primer uso los hace el servicio con su propia identidad técnica (cliente `commercial-relationship-service`).
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- Ejercicio 1: la adopción registra el primer uso del producto global.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<AGUJA>",
  "internal_code": "000537",
  "display_name": "AGUJA 18GX1 1/2 CAJAX100 RFZC18B RYMCO"
}
```

**Guardar:** `id` → `<AGUJA>`

## 3. Adoptar el irbesartán (fila 16577)

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

- Ejercicio 1: la adopción registra el primer uso del producto global.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<IRBESARTAN>",
  "internal_code": "022315",
  "display_name": "IRBESARTAN+HIDROCLOROTIAZIDA (IRBESARTAN/HCT) 150+12.5MG TABLETA CAJAX30MK"
}
```

**Guardar:** `id` → `<IRBESARTAN>`

## 4. Adoptar la caja x100 del acetaminofén

```http
POST /api/v1/companies/<EMPRESA>/company-product-presentations
```

```json
{
  "company_product_id": "<ACETAMINOFEN>",
  "global_product_presentation_id": "<GPRES_CAJA>",
  "sku": "ACE-CJ100"
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_product_presentations:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `company_product_presentations` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `company_product_presentations` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- Ejercicio 4. El SKU es de la empresa y servirá para buscar el producto.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<PRES_CAJA>",
  "company_product_id": "<ACETAMINOFEN>",
  "sku": "ACE-CJ100"
}
```

**Guardar:** `id` → `<PRES_CAJA>`

## 5. Adoptar el sobre x10 del acetaminofén

```http
POST /api/v1/companies/<EMPRESA>/company-product-presentations
```

```json
{
  "company_product_id": "<ACETAMINOFEN>",
  "global_product_presentation_id": "<GPRES_SOBRE>",
  "sku": "ACE-SB10"
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_product_presentations:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `company_product_presentations` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `company_product_presentations` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- Dos presentaciones del mismo producto: la búsqueda por SKU no repite el producto.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<PRES_SOBRE>",
  "company_product_id": "<ACETAMINOFEN>",
  "sku": "ACE-SB10"
}
```

**Guardar:** `id` → `<PRES_SOBRE>`

---

[← Paso anterior](01-consultar-datos.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](03-buscar.md)
