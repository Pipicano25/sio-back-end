# Paso 05 de 05 — Evaluar un lote, pedir presentaciones y rechazos

Ejercicio 10 — Búsqueda progresiva de productos y presentaciones por productos · [← Paso anterior](04-continuar.md) · [Orden del ejercicio](ORDEN.md)

**Objetivo:** Comprobar filtros sobre un lote de ids, traer las presentaciones de varios productos y los errores.

**Necesita (de pasos anteriores):** `<EMPRESA>`, `<ACETAMINOFEN>`, `<AGUJA>`, `<GP_AGUJA>` — pasos [01](01-consultar-datos.md), [02](02-adoptar-productos.md)

---

## 1. ¿Cuáles de estos productos coinciden con «aguja»?

```http
POST /api/v1/companies/<EMPRESA>/company-products/search
```

```json
{
  "search": "aguja",
  "company_product_ids": [
    "<ACETAMINOFEN>",
    "<AGUJA>"
  ],
  "limit": 10
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_products:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:commercial-relationship:company_products:read`), `ventas.test` (por `perm:commercial-relationship:company_products:read`), `inventario.test` (por `perm:commercial-relationship:company_products:read`), `reportes.test` (por `perm:commercial-relationship:company_products:read`), `consulta.test` (por `perm:commercial-relationship:company_products:read`)
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- Modo evaluador: solo se miran los ids enviados (hasta 100) y se aplican los filtros.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "id": "<AGUJA>",
      "internal_code": "000537",
      "display_name": "AGUJA 18GX1 1/2 CAJAX100 RFZC18B RYMCO",
      "position": {
        "k": [
          "AGUJA 18GX1 1/2 CAJAX100 RFZC18B RYMCO"
        ],
        "id": "<AGUJA>"
      }
    }
  ],
  "has_more": false
}
```

## 2. Presentaciones del acetaminofén y la aguja

```http
POST /api/v1/companies/<EMPRESA>/company-product-presentations/by-products
```

```json
{
  "company_product_ids": [
    "<ACETAMINOFEN>",
    "<AGUJA>"
  ]
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_product_presentations:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:commercial-relationship:company_product_presentations:read`), `ventas.test` (por `perm:commercial-relationship:company_product_presentations:read`), `reportes.test` (por `perm:commercial-relationship:company_product_presentations:read`), `consulta.test` (por `perm:commercial-relationship:company_product_presentations:read`)
- ❌ **No pueden (responde `403`):** `inventario.test` — no tiene ningún permiso sobre `company_product_presentations` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- Una sola llamada para varios productos, en orden `company_product_id, id`. Vuelven las dos presentaciones del acetaminofén (`ACE-CJ100` y `ACE-SB10`); la aguja no tiene presentaciones adoptadas: no aparece ninguna suya.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "company_product_id": "<ACETAMINOFEN>",
      "status": "ACTIVE"
    },
    {
      "company_product_id": "<ACETAMINOFEN>",
      "status": "ACTIVE"
    }
  ]
}
```

## 3. Pedir 101 productos (rechazado)

```http
POST /api/v1/companies/<EMPRESA>/company-products/search
```

```json
{
  "limit": 101
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_products:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:commercial-relationship:company_products:read`), `ventas.test` (por `perm:commercial-relationship:company_products:read`), `inventario.test` (por `perm:commercial-relationship:company_products:read`), `reportes.test` (por `perm:commercial-relationship:company_products:read`), `consulta.test` (por `perm:commercial-relationship:company_products:read`)
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- `limit` admite de 1 a 100: `422 VALIDATION_ERROR`.

**Respuesta esperada (error) — `422 Unprocessable Content`** (abreviada)

```json
{
  "status": 422,
  "code": "COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR",
  "detail": "La solicitud contiene datos inválidos.",
  "errors": [
    {
      "field": "limit",
      "message": "Input should be less than or equal to 100",
      "code": "VALIDATION_ERROR"
    }
  ]
}
```

## 4. Enviar los dos tipos de ids a la vez (rechazado)

```http
POST /api/v1/companies/<EMPRESA>/company-products/search
```

```json
{
  "company_product_ids": [
    "<AGUJA>"
  ],
  "global_product_ids": [
    "<GP_AGUJA>"
  ],
  "limit": 10
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_products:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:commercial-relationship:company_products:read`), `ventas.test` (por `perm:commercial-relationship:company_products:read`), `inventario.test` (por `perm:commercial-relationship:company_products:read`), `reportes.test` (por `perm:commercial-relationship:company_products:read`), `consulta.test` (por `perm:commercial-relationship:company_products:read`)
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- Se usa `company_product_ids` **o** `global_product_ids`: `422 VALIDATION_ERROR`.

**Respuesta esperada (error) — `422 Unprocessable Content`** (abreviada)

```json
{
  "status": 422,
  "code": "COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR",
  "detail": "La solicitud contiene datos inválidos.",
  "errors": [
    {
      "field": "body",
      "message": "Use company_product_ids o global_product_ids, no ambos.",
      "code": "VALIDATION_ERROR"
    }
  ]
}
```

---

[← Paso anterior](04-continuar.md) · [Orden del ejercicio](ORDEN.md)
