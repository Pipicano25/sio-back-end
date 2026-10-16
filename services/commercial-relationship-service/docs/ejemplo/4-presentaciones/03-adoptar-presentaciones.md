# Paso 03 de 05 — Adoptar presentaciones y cambiar la predeterminada

Ejercicio 4 — Presentaciones de un producto empresarial · [← Paso anterior](02-adoptar-producto.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](04-rechazos.md)

**Objetivo:** Adoptar la caja como predeterminada de compra y luego el sobre, que toma la marca.

**Necesita (de pasos anteriores):** `<EMPRESA>`, `<PRODUCTO>`, `<GPRES_CAJA>`, `<GPRES_SOBRE>` — pasos [01](01-consultar-datos.md), [02](02-adoptar-producto.md)

**Deja guardado para los siguientes pasos:** `<PRES_CAJA>`, `<PRES_SOBRE>`

---

## 1. Adoptar la caja x100 como predeterminada de compra

```http
POST /api/v1/companies/<EMPRESA>/company-product-presentations
```

```json
{
  "company_product_id": "<PRODUCTO>",
  "global_product_presentation_id": "<GPRES_CAJA>",
  "sku": "ACE-CJ100",
  "is_default_purchase": true
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_product_presentations:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `company_product_presentations` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `company_product_presentations` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- El servicio comprueba en Product Catalog que la presentación esté `ACTIVE`, sea elegible y sea del mismo producto global, y registra su primer uso.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<PRES_CAJA>",
  "company_product_id": "<PRODUCTO>",
  "global_product_presentation_id": "<GPRES_CAJA>",
  "internal_code": null,
  "sku": "ACE-CJ100",
  "is_purchasable": true,
  "is_sellable": true,
  "is_default_purchase": true,
  "is_default_sale": false,
  "status": "ACTIVE",
  "version": 1
}
```

**Guardar:** `id` → `<PRES_CAJA>`

## 2. Adoptar el sobre x10 y marcarlo predeterminado de compra

```http
POST /api/v1/companies/<EMPRESA>/company-product-presentations
```

```json
{
  "company_product_id": "<PRODUCTO>",
  "global_product_presentation_id": "<GPRES_SOBRE>",
  "sku": "ACE-SB10",
  "is_default_purchase": true
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_product_presentations:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `company_product_presentations` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `company_product_presentations` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- Marcar una nueva predeterminada retira la de la caja en la misma operación (aclaración 4).

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<PRES_SOBRE>",
  "company_product_id": "<PRODUCTO>",
  "global_product_presentation_id": "<GPRES_SOBRE>",
  "internal_code": null,
  "sku": "ACE-SB10",
  "is_purchasable": true,
  "is_sellable": true,
  "is_default_purchase": true,
  "is_default_sale": false,
  "status": "ACTIVE",
  "version": 1
}
```

**Guardar:** `id` → `<PRES_SOBRE>`

## 3. Consultar la caja: ya no es predeterminada

```http
GET /api/v1/company-product-presentations/<PRES_CAJA>
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_product_presentations:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:commercial-relationship:company_product_presentations:read`), `ventas.test` (por `perm:commercial-relationship:company_product_presentations:read`), `reportes.test` (por `perm:commercial-relationship:company_product_presentations:read`), `consulta.test` (por `perm:commercial-relationship:company_product_presentations:read`)
- ❌ **No pueden (responde `403`):** `inventario.test` — no tiene ningún permiso sobre `company_product_presentations` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- La caja perdió la marca y subió a `version` 2, con `updated_by` del usuario que marcó el sobre (Principio VII).

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "id": "<PRES_CAJA>",
  "company_product_id": "<PRODUCTO>",
  "global_product_presentation_id": "<GPRES_CAJA>",
  "internal_code": null,
  "sku": "ACE-CJ100",
  "is_purchasable": true,
  "is_sellable": true,
  "is_default_purchase": false,
  "is_default_sale": false,
  "status": "ACTIVE",
  "version": 2
}
```

---

[← Paso anterior](02-adoptar-producto.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](04-rechazos.md)
