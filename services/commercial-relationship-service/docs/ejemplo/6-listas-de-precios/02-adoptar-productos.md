# Paso 02 de 05 — Adoptar los productos

Ejercicio 6 — Listas de precios y precio aplicable · [← Paso anterior](01-consultar-datos.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](03-lista-y-precio.md)

**Objetivo:** Crear los productos empresariales.

**Necesita (de pasos anteriores):** `<EMPRESA>`, `<GP_IRBESARTAN>`, `<GP_ACETAMINOFEN>` — pasos [01](01-consultar-datos.md)

**Deja guardado para los siguientes pasos:** `<IRBESARTAN>`, `<ACETAMINOFEN>`

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
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `company_products` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `company_products` de `commercial-relationship`
- ℹ️ Adoptar no exige permisos en Product Catalog al usuario: la elegibilidad y el registro de primer uso los hace el servicio con su propia identidad técnica (cliente `commercial-relationship-service`).
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- Ejercicio 1.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<IRBESARTAN>",
  "internal_code": "022315",
  "sale_price": "0.00"
}
```

**Guardar:** `id` → `<IRBESARTAN>`

## 2. Adoptar el acetaminofén con precio simple (ficticio)

```http
POST /api/v1/companies/<EMPRESA>/company-products
```

```json
{
  "global_product_id": "<GP_ACETAMINOFEN>",
  "internal_code": "000045",
  "display_name": "ACETAMINOFEN (ADOREM) 500MG TABLETA CAJAX100 SIEGFRIED",
  "currency_code": "COP",
  "sale_price": "12000.00"
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_products:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `company_products` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `company_products` de `commercial-relationship`
- ℹ️ Adoptar no exige permisos en Product Catalog al usuario: la elegibilidad y el registro de primer uso los hace el servicio con su propia identidad técnica (cliente `commercial-relationship-service`).
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- `sale_price` es el precio simple de respaldo cuando no hay precio de lista (FR-056).

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<ACETAMINOFEN>",
  "internal_code": "000045",
  "sale_price": "12000.00"
}
```

**Guardar:** `id` → `<ACETAMINOFEN>`

---

[← Paso anterior](01-consultar-datos.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](03-lista-y-precio.md)
