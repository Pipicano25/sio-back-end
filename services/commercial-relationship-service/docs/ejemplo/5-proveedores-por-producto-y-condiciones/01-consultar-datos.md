# Paso 01 de 04 — Consultar la empresa, el producto, la presentación, el proveedor y los tipos

Ejercicio 5 — Proveedores por producto y condiciones de pago · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](02-preparar.md)

**Objetivo:** Obtener los identificadores de los otros servicios.

**Necesita (de pasos anteriores):** `<NIT>`

**Deja guardado para los siguientes pasos:** `<EMPRESA>`, `<GP_ACETAMINOFEN>`, `<GPRES_CAJA>`, `<UNIDAD_BASE>`, `<ORG_PROVEEDOR>`, `<TIPO_CASH>`, `<TIPO_CREDIT>`

---

## 1. Consultar la empresa DROGUERÍA COMPRAS FICTICIA S.A.S. en Operational Context

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

## 3. Consultar la presentación global Caja x100 en Product Catalog

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
    "name": "Caja x100 (nombre en Product Catalog)",
    "status": "ACTIVE",
    "eligible_for_adoption": true
  }
]
```

**Guardar:** `[0].id` → `<GPRES_CAJA>`

## 4. Consultar la unidad base del producto global en Product Catalog

> **Otro servicio:** esta llamada va a **Product Catalog Service**, no a Commercial Relationship. No se ejecuta en la validación automática: su resultado se simula.

```http
GET http://localhost:8003/api/v1/products/<GP_ACETAMINOFEN>
```

**Permiso que exige la URL:** `perm:product-catalog:products:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:product-catalog:all:read`), `ventas.test` (por `perm:product-catalog:all:read`), `inventario.test` (por `perm:product-catalog:all:read`), `reportes.test` (por `perm:product-catalog:products:read`), `consulta.test` (por `perm:product-catalog:products:read`)

**Por qué se hace así**

- En el MVP no hay conversión de unidades (OP-01): la unidad de compra de un producto de proveedor es siempre la **unidad base** del producto global (DS-07). El servicio la verifica con su identidad técnica.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "id": "<GP_ACETAMINOFEN>",
  "base_unit_id": "<UNIDAD_BASE>",
  "status": "ACTIVE"
}
```

**Guardar:** `base_unit_id` → `<UNIDAD_BASE>`

## 5. Consultar la organización LABORATORIO PROVEEDOR FICTICIO S.A.S. en Party Identity

> **Otro servicio:** esta llamada va a **Party Identity Service**, no a Commercial Relationship. No se ejecuta en la validación automática: su resultado se simula.

```http
GET http://localhost:8002/api/v1/organization-identities?search=<NIT>
```

**Permiso que exige la URL:** `perm:party-identity:organization_identities:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:party-identity:organization_identities:read`), `ventas.test` (por `perm:party-identity:organization_identities:read`), `reportes.test` (por `perm:party-identity:organization_identities:read`), `consulta.test` (por `perm:party-identity:organization_identities:read`)
- ❌ **No pueden (responde `403`):** `inventario.test` — no tiene ningún permiso sobre `organization_identities` de `party-identity`

**Por qué se hace así**

- Commercial Relationship **no guarda** la razón social ni el NIT: solo el `id` de la `OrganizationIdentity` (Principio III). El NIT real se toma de una fuente oficial (RUT, RUES).

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "id": "<ORG_PROVEEDOR>",
      "identification_type": "NIT",
      "identification_number": "<NIT obtenido del RUT; dato ficticio aquí>",
      "legal_name": "LABORATORIO PROVEEDOR FICTICIO S.A.S.",
      "status": "ACTIVE"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

**Guardar:** `items[0].id` → `<ORG_PROVEEDOR>`

## 6. Consultar el tipo de condición de pago CASH en Payment Reference

> **Otro servicio:** esta llamada va a **Payment Reference Service**, no a Commercial Relationship. No se ejecuta en la validación automática: su resultado se simula.

```http
GET http://localhost:8105/global-payment-condition-types?code=CASH
```

**Permiso que exige la URL:** `perm:payment-reference:global_payment_condition_types:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:payment-reference:all:read`), `ventas.test` (por `perm:payment-reference:all:read`), `reportes.test` (por `perm:payment-reference:global_payment_condition_types:read`), `consulta.test` (por `perm:payment-reference:global_payment_condition_types:read`)
- ❌ **No pueden (responde `403`):** `inventario.test` — no tiene ningún permiso sobre `global_payment_condition_types` de `payment-reference`

**Por qué se hace así**

- Commercial Relationship **no guarda** el código ni el nombre del tipo: solo su `id`. Lo consulta con su identidad técnica para validar que esté `ACTIVE` y que el plazo corresponda (`CASH` → 0 días; `CREDIT` y `FINANCING` → más de 0, FR-033).

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "id": "<TIPO_CASH>",
      "code": "CASH",
      "name": "<nombre del tipo>",
      "status": "ACTIVE"
    }
  ]
}
```

**Guardar:** `items[0].id` → `<TIPO_CASH>`

## 7. Consultar el tipo de condición de pago CREDIT en Payment Reference

> **Otro servicio:** esta llamada va a **Payment Reference Service**, no a Commercial Relationship. No se ejecuta en la validación automática: su resultado se simula.

```http
GET http://localhost:8105/global-payment-condition-types?code=CREDIT
```

**Permiso que exige la URL:** `perm:payment-reference:global_payment_condition_types:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:payment-reference:all:read`), `ventas.test` (por `perm:payment-reference:all:read`), `reportes.test` (por `perm:payment-reference:global_payment_condition_types:read`), `consulta.test` (por `perm:payment-reference:global_payment_condition_types:read`)
- ❌ **No pueden (responde `403`):** `inventario.test` — no tiene ningún permiso sobre `global_payment_condition_types` de `payment-reference`

**Por qué se hace así**

- Commercial Relationship **no guarda** el código ni el nombre del tipo: solo su `id`. Lo consulta con su identidad técnica para validar que esté `ACTIVE` y que el plazo corresponda (`CASH` → 0 días; `CREDIT` y `FINANCING` → más de 0, FR-033).

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "id": "<TIPO_CREDIT>",
      "code": "CREDIT",
      "name": "<nombre del tipo>",
      "status": "ACTIVE"
    }
  ]
}
```

**Guardar:** `items[0].id` → `<TIPO_CREDIT>`

---

[Orden del ejercicio](ORDEN.md) · [Paso siguiente →](02-preparar.md)
