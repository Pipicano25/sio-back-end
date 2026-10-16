# Paso 01 de 05 — Consultar la empresa y el producto global

Ejercicio 9 — Actualizaciones automáticas de precio · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](02-preparar-la-politica.md)

**Objetivo:** Obtener `<EMPRESA>`, el producto y su presentación global.

**Deja guardado para los siguientes pasos:** `<EMPRESA>`, `<GP_ACETAMINOFEN>`, `<GPRES_CAJA>`

---

## 1. Consultar la empresa DROGUERÍA ACTUALIZACIONES FICTICIA S.A.S. en Operational Context

> **Otro servicio:** esta llamada va a **Operational Context Service**, no a Commercial Relationship. No se ejecuta en la validación automática: su resultado se simula.

```http
GET http://localhost:8004/api/v1/me/operational-context
```

**Permiso que exige la URL:** `perm:operational-context:application_users:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:operational-context:all:read`), `ventas.test` (por `perm:operational-context:all:read`), `inventario.test` (por `perm:operational-context:all:read`), `reportes.test` (por `perm:operational-context:application_users:read`), `consulta.test` (por `perm:operational-context:application_users:read`)

**Por qué se hace así**

- Commercial Relationship **no guarda** empresas: usa el `company_id` de Operational Context y, en cada solicitud, le pregunta si el usuario tiene membresía `ACTIVE` en ella (DS-02).
- `me/operational-context` lista las empresas donde el usuario es miembro: de ahí se toma el `id`.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "keycloak_user_id": "<sub del usuario>",
  "memberships": [
    {
      "application_user_id": "<id generado>",
      "company_id": "<EMPRESA>",
      "company_status": "ACTIVE",
      "status": "ACTIVE",
      "branches": []
    }
  ]
}
```

**Guardar:** `memberships[0].company_id` → `<EMPRESA>`

## 2. Consultar el producto global ACETAMINOFEN (ADOREM) 500MG TABLETA CAJAX100 SIEGFRIED en Product Catalog

> **Otro servicio:** esta llamada va a **Product Catalog Service**, no a Commercial Relationship. No se ejecuta en la validación automática: su resultado se simula.

```http
GET http://localhost:8003/api/v1/products/by-identifier/7707355056876
```

**Permiso que exige la URL:** `perm:product-catalog:products:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:product-catalog:all:read`), `ventas.test` (por `perm:product-catalog:all:read`), `inventario.test` (por `perm:product-catalog:all:read`), `reportes.test` (por `perm:product-catalog:products:read`), `consulta.test` (por `perm:product-catalog:products:read`)

**Por qué se hace así**

- Commercial Relationship **no copia** el nombre canónico, la marca ni la unidad del producto global: solo guarda su `id` (`global_product_id`, FR-018).
- Al adoptar, el servicio vuelve a comprobar en Product Catalog que esté `ACTIVE` y completo, con su propia identidad técnica.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "product": {
    "id": "<GP_ACETAMINOFEN>",
    "canonical_name": "ACETAMINOFEN (ADOREM) 500MG TABLETA CAJAX100 SIEGFRIED",
    "status": "ACTIVE",
    "eligible_for_adoption": true
  },
  "identifier": "7707355056876",
  "is_current": true
}
```

**Guardar:** `product.id` → `<GP_ACETAMINOFEN>`

## 3. Consultar la presentación global caja x100 del acetaminofén en Product Catalog

> **Otro servicio:** esta llamada va a **Product Catalog Service**, no a Commercial Relationship. No se ejecuta en la validación automática: su resultado se simula.

```http
GET http://localhost:8003/api/v1/products/<GP_ACETAMINOFEN>/presentations
```

**Permiso que exige la URL:** `perm:product-catalog:products:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:product-catalog:all:read`), `ventas.test` (por `perm:product-catalog:all:read`), `inventario.test` (por `perm:product-catalog:all:read`), `reportes.test` (por `perm:product-catalog:products:read`), `consulta.test` (por `perm:product-catalog:products:read`)

**Por qué se hace así**

- Commercial Relationship **no copia** el nombre, la cantidad base ni el empaque de la presentación global: solo guarda su `id` (`global_product_presentation_id`, FR-017).
- Al adoptar, el servicio vuelve a comprobar en Product Catalog que esté `ACTIVE`, sea elegible y pertenezca al mismo producto global, y registra su **primer uso** con su identidad técnica.

**Respuesta esperada — `200 OK`** (abreviada)

```json
[
  {
    "id": "<GPRES_CAJA>",
    "global_product_id": "<GP_ACETAMINOFEN>",
    "name": "caja x100 del acetaminofén (nombre en Product Catalog)",
    "status": "ACTIVE",
    "eligible_for_adoption": true
  }
]
```

**Guardar:** `[0].id` → `<GPRES_CAJA>`

---

[Orden del ejercicio](ORDEN.md) · [Paso siguiente →](02-preparar-la-politica.md)
