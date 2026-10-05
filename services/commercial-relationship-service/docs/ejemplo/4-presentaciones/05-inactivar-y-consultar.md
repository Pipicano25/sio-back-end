# Paso 05 de 05 — Inactivar la predeterminada y consultar

Ejercicio 4 — Presentaciones de un producto empresarial · [← Paso anterior](04-rechazos.md) · [Orden del ejercicio](ORDEN.md)

**Objetivo:** Inactivar el sobre (pierde la marca) y listar las presentaciones del producto.

**Necesita (de pasos anteriores):** `<PRES_SOBRE>`, `<EMPRESA>`, `<PRODUCTO>` — pasos [01](01-consultar-datos.md), [02](02-adoptar-producto.md), [03](03-adoptar-presentaciones.md)

---

## 1. Inactivar el sobre

```http
POST /api/v1/company-product-presentations/<PRES_SOBRE>/deactivate
```

```json
{
  "version": 1
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_product_presentations:delete`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`)
- ❌ **No pueden (responde `403`):** `supervisor.test` — sobre `company_product_presentations` solo tiene `create`, `read`, `update`; le falta `delete`; `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `company_product_presentations` solo tienen `read`; les falta `delete`; `inventario.test` — no tiene ningún permiso sobre `company_product_presentations` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- Inactivar exige `delete` y retira la marca de predeterminada (DS-05).

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "id": "<PRES_SOBRE>",
  "company_product_id": "<PRODUCTO>",
  "global_product_presentation_id": "<GPRES_SOBRE>",
  "internal_code": null,
  "sku": "ACE-SB10",
  "is_purchasable": true,
  "is_sellable": true,
  "is_default_purchase": false,
  "is_default_sale": false,
  "status": "INACTIVE",
  "version": 2
}
```

## 2. Listar todas las presentaciones del producto

```http
GET /api/v1/companies/<EMPRESA>/company-product-presentations?company_product_id=<PRODUCTO>&status=ALL
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_product_presentations:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:commercial-relationship:all:read`), `ventas.test` (por `perm:commercial-relationship:all:read`), `reportes.test` (por `perm:commercial-relationship:company_product_presentations:read`), `consulta.test` (por `perm:commercial-relationship:company_product_presentations:read`)
- ❌ **No pueden (responde `403`):** `inventario.test` — no tiene ningún permiso sobre `company_product_presentations` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- Sin `status` solo se listan las `ACTIVE`; `status=ALL` incluye las inactivas: aquí la caja (`ACTIVE`) y el sobre (`INACTIVE`, sin marca).

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "total_records": 2,
  "page": 1,
  "page_size": 20
}
```

---

[← Paso anterior](04-rechazos.md) · [Orden del ejercicio](ORDEN.md)
