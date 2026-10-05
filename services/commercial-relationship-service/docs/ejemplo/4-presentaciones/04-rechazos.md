# Paso 04 de 05 — Rechazos esperados

Ejercicio 4 — Presentaciones de un producto empresarial · [← Paso anterior](03-adoptar-presentaciones.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](05-inactivar-y-consultar.md)

**Objetivo:** Presentación de otro producto y adopción repetida.

**Necesita (de pasos anteriores):** `<EMPRESA>`, `<PRODUCTO>`, `<GPRES_AGUJA>`, `<GPRES_CAJA>` — pasos [01](01-consultar-datos.md), [02](02-adoptar-producto.md)

---

## 1. Adoptar la caja de la aguja para el acetaminofén (rechazado)

```http
POST /api/v1/companies/<EMPRESA>/company-product-presentations
```

```json
{
  "company_product_id": "<PRODUCTO>",
  "global_product_presentation_id": "<GPRES_AGUJA>"
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_product_presentations:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `company_product_presentations` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `company_product_presentations` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- La presentación pertenece a otro producto global: `422 GLOBAL_PRESENTATION_OF_OTHER_PRODUCT` sin registrar primer uso.

**Respuesta esperada (error) — `422 Unprocessable Content`** (abreviada)

```json
{
  "status": 422,
  "code": "COMMERCIAL_RELATIONSHIP.GLOBAL_PRESENTATION_OF_OTHER_PRODUCT",
  "detail": "La presentación global no pertenece al producto global adoptado.",
  "errors": [
    {
      "field": "global_product_presentation_id",
      "message": "La presentación global no pertenece al producto global adoptado.",
      "code": "GLOBAL_PRESENTATION_OF_OTHER_PRODUCT"
    }
  ]
}
```

## 2. Adoptar otra vez la caja (rechazado)

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

- Cada presentación se adopta una sola vez por producto, en cualquier estado: `409 DUPLICATE_PRESENTATION_ADOPTION`.

**Respuesta esperada (error) — `409 Conflict`** (abreviada)

```json
{
  "status": 409,
  "code": "COMMERCIAL_RELATIONSHIP.DUPLICATE_PRESENTATION_ADOPTION",
  "detail": "La presentación ya está adoptada para este producto; si está inactiva, reactívela.",
  "errors": [
    {
      "field": "global_product_presentation_id",
      "message": "La presentación ya está adoptada para este producto; si está inactiva, reactívela.",
      "code": "DUPLICATE_PRESENTATION_ADOPTION"
    }
  ]
}
```

---

[← Paso anterior](03-adoptar-presentaciones.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](05-inactivar-y-consultar.md)
