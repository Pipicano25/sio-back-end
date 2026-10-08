# Paso 02 de 04 — Adoptar el producto y la presentación y seleccionar el proveedor

Ejercicio 5 — Proveedores por producto y condiciones de pago · [← Paso anterior](01-consultar-datos.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](03-productos-de-proveedor.md)

**Objetivo:** Crear lo que el producto de proveedor referencia.

**Necesita (de pasos anteriores):** `<EMPRESA>`, `<GP_ACETAMINOFEN>`, `<GPRES_CAJA>`, `<ORG_PROVEEDOR>` — pasos [01](01-consultar-datos.md)

**Deja guardado para los siguientes pasos:** `<PRODUCTO>`, `<PRES_CAJA>`, `<PROVEEDOR>`

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
  "id": "<PRODUCTO>",
  "status": "ACTIVE"
}
```

**Guardar:** `id` → `<PRODUCTO>`

## 2. Adoptar la caja x100

```http
POST /api/v1/companies/<EMPRESA>/company-product-presentations
```

```json
{
  "company_product_id": "<PRODUCTO>",
  "global_product_presentation_id": "<GPRES_CAJA>"
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_product_presentations:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `company_product_presentations` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `company_product_presentations` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- Ejercicio 4. Es comprable por defecto.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<PRES_CAJA>",
  "is_purchasable": true,
  "status": "ACTIVE"
}
```

**Guardar:** `id` → `<PRES_CAJA>`

## 3. Seleccionar el proveedor

```http
POST /api/v1/companies/<EMPRESA>/company-suppliers
```

```json
{
  "organization_identity_id": "<ORG_PROVEEDOR>",
  "internal_code": "PRV-0001",
  "display_name": "Laboratorio proveedor (ficticio)"
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_suppliers:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `company_suppliers` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `company_suppliers` de `commercial-relationship`
- ℹ️ Igual que los clientes: el token debe poder leer organizaciones y personas de contacto en Party Identity y la empresa en Operational Context.
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- Ejercicio 3.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<PROVEEDOR>",
  "status": "ACTIVE"
}
```

**Guardar:** `id` → `<PROVEEDOR>`

---

[← Paso anterior](01-consultar-datos.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](03-productos-de-proveedor.md)
