# Paso 02 de 03 — Adoptar los productos

Ejercicio 8 — Tasa de impuesto de compra del producto · [← Paso anterior](01-consultar-datos.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](03-configurar-tasas.md)

**Objetivo:** Productos sin tasa configurada.

**Necesita (de pasos anteriores):** `<EMPRESA>`, `<GP_ACETAMINOFEN>`, `<GP_IRBESARTAN>` — pasos [01](01-consultar-datos.md)

**Deja guardado para los siguientes pasos:** `<ACETAMINOFEN>`, `<IRBESARTAN>`

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

- `purchase_tax_percentage` nace en `null`: **sin configurar**.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<ACETAMINOFEN>",
  "internal_code": "000045",
  "purchase_tax_percentage": null,
  "version": 1
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

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<IRBESARTAN>",
  "internal_code": "022315",
  "purchase_tax_percentage": null,
  "version": 1
}
```

**Guardar:** `id` → `<IRBESARTAN>`

---

[← Paso anterior](01-consultar-datos.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](03-configurar-tasas.md)
