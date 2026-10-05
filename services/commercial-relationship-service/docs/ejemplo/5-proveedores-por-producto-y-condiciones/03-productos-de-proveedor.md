# Paso 03 de 04 — Registrar qué suministra el proveedor

Ejercicio 5 — Proveedores por producto y condiciones de pago · [← Paso anterior](02-preparar.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](04-condiciones-de-pago.md)

**Objetivo:** Relación general, rechazo por unidad, relación por presentación y rechazo por repetición.

**Necesita (de pasos anteriores):** `<EMPRESA>`, `<PROVEEDOR>`, `<PRODUCTO>`, `<UNIDAD_BASE>`, `<PRES_CAJA>` — pasos [01](01-consultar-datos.md), [02](02-preparar.md)

**Deja guardado para los siguientes pasos:** `<PRV_GENERAL>`

---

## 1. Registrar la relación general

```http
POST /api/v1/companies/<EMPRESA>/supplier-products
```

```json
{
  "company_supplier_id": "<PROVEEDOR>",
  "company_product_id": "<PRODUCTO>",
  "supplier_product_code": "ACETAMINOFEN 500MG TABLETA CAJAX100 SIEGFRIED",
  "purchase_unit_id": "<UNIDAD_BASE>",
  "currency_code": "COP",
  "negotiated_unit_cost": "12500.5000",
  "minimum_order_quantity": "10",
  "is_preferred": true
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:supplier_products:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `supplier_products` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `supplier_products` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- El servicio exige proveedor y producto `ACTIVE` y comprueba en Product Catalog que la unidad sea la base. Se marca como proveedor preferido del producto.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<PRV_GENERAL>",
  "company_supplier_id": "<PROVEEDOR>",
  "company_product_id": "<PRODUCTO>",
  "company_product_presentation_id": null,
  "supplier_product_code": "ACETAMINOFEN 500MG TABLETA CAJAX100 SIEGFRIED",
  "purchase_unit_id": "<UNIDAD_BASE>",
  "minimum_order_quantity": "10.0000",
  "pack_quantity": "1.0000",
  "negotiated_unit_cost": "12500.5000",
  "currency_code": "COP",
  "is_preferred": true,
  "status": "ACTIVE",
  "version": 1
}
```

**Guardar:** `id` → `<PRV_GENERAL>`

## 2. Registrar con otra unidad (rechazado)

```http
POST /api/v1/companies/<EMPRESA>/supplier-products
```

```json
{
  "company_supplier_id": "<PROVEEDOR>",
  "company_product_id": "<PRODUCTO>",
  "company_product_presentation_id": "<PRES_CAJA>",
  "purchase_unit_id": "7c7c7c7c-0000-4000-8000-00000000ffff",
  "currency_code": "COP"
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:supplier_products:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `supplier_products` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `supplier_products` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- Sin conversión de unidades en el MVP: `422 PURCHASE_UNIT_NOT_BASE_UNIT`.

**Respuesta esperada (error) — `422 Unprocessable Content`** (abreviada)

```json
{
  "status": 422,
  "code": "COMMERCIAL_RELATIONSHIP.PURCHASE_UNIT_NOT_BASE_UNIT",
  "detail": "La unidad de compra debe ser la unidad base del producto global.",
  "errors": [
    {
      "field": "purchase_unit_id",
      "message": "La unidad de compra debe ser la unidad base del producto global.",
      "code": "PURCHASE_UNIT_NOT_BASE_UNIT"
    }
  ]
}
```

## 3. Registrar la relación de la caja x100

```http
POST /api/v1/companies/<EMPRESA>/supplier-products
```

```json
{
  "company_supplier_id": "<PROVEEDOR>",
  "company_product_id": "<PRODUCTO>",
  "company_product_presentation_id": "<PRES_CAJA>",
  "purchase_unit_id": "<UNIDAD_BASE>",
  "currency_code": "COP",
  "pack_quantity": "100"
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:supplier_products:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `supplier_products` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `supplier_products` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- Coexiste con la general: la presentación es parte de la combinación única (aclaración 3).

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<id generado>",
  "company_supplier_id": "<PROVEEDOR>",
  "company_product_id": "<PRODUCTO>",
  "company_product_presentation_id": "<PRES_CAJA>",
  "supplier_product_code": null,
  "purchase_unit_id": "<UNIDAD_BASE>",
  "minimum_order_quantity": "0.0000",
  "pack_quantity": "100.0000",
  "negotiated_unit_cost": null,
  "currency_code": "COP",
  "is_preferred": false,
  "status": "ACTIVE",
  "version": 1
}
```

## 4. Repetir la relación general (rechazado)

```http
POST /api/v1/companies/<EMPRESA>/supplier-products
```

```json
{
  "company_supplier_id": "<PROVEEDOR>",
  "company_product_id": "<PRODUCTO>",
  "purchase_unit_id": "<UNIDAD_BASE>",
  "currency_code": "COP"
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:supplier_products:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `supplier_products` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `supplier_products` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- Ya hay una relación `ACTIVE` sin presentación: `409 DUPLICATE_SUPPLIER_PRODUCT`.

**Respuesta esperada (error) — `409 Conflict`** (abreviada)

```json
{
  "status": 409,
  "code": "COMMERCIAL_RELATIONSHIP.DUPLICATE_SUPPLIER_PRODUCT",
  "detail": "Ya existe una relación activa para este proveedor, producto y presentación."
}
```

---

[← Paso anterior](02-preparar.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](04-condiciones-de-pago.md)
