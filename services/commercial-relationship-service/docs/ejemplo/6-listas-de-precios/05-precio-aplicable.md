# Paso 05 de 05 — Resolver el precio aplicable

Ejercicio 6 — Listas de precios y precio aplicable · [← Paso anterior](04-cambiar-precio.md) · [Orden del ejercicio](ORDEN.md)

**Objetivo:** Precio de la presentación en la lista y presentación sin precio (sin respaldo).

**Necesita (de pasos anteriores):** `<EMPRESA>`, `<IRBESARTAN>`, `<PRES_IRBE>`, `<ACETAMINOFEN>`, `<PRES_ACETA>`, `<LISTA>` — pasos [01](01-consultar-datos.md), [02](02-adoptar-productos.md), [03](03-lista-y-precio.md)

---

## 1. Resolver hoy: irbesartán y acetaminofén con la lista predeterminada

```http
POST /api/v1/companies/<EMPRESA>/applicable-prices/resolve
```

```json
{
  "at": "2027-01-01T00:00:00Z",
  "lines": [
    {
      "line_id": "1",
      "company_product_id": "<IRBESARTAN>",
      "company_product_presentation_id": "<PRES_IRBE>"
    },
    {
      "line_id": "2",
      "company_product_id": "<ACETAMINOFEN>",
      "company_product_presentation_id": "<PRES_ACETA>"
    }
  ]
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:price_list_items:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:commercial-relationship:all:read`), `ventas.test` (por `perm:commercial-relationship:all:read`), `reportes.test` (por `perm:commercial-relationship:price_list_items:read`), `consulta.test` (por `perm:commercial-relationship:price_list_items:read`)
- ❌ **No pueden (responde `403`):** `inventario.test` — no tiene ningún permiso sobre `price_list_items` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- Línea 1: precio de la caja x30 en la lista predeterminada (`PRICE_LIST_ITEM`, base `PRESENTATION`). Línea 2: la caja del acetaminofén no tiene precio → `NO_PRICE_IN_LIST`, sin respaldo (spec 019): no se puede vender hasta registrar su precio.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "line_id": "1",
      "resolution": "PRICE_LIST_ITEM",
      "basis": "PRESENTATION",
      "unit_price": "30420.00",
      "currency_code": "COP"
    },
    {
      "line_id": "2",
      "resolution": "NO_PRICE_IN_LIST",
      "basis": null,
      "unit_price": null,
      "currency_code": null
    }
  ]
}
```

## 2. Resolver con la lista explícita para el acetaminofén

```http
POST /api/v1/companies/<EMPRESA>/applicable-prices/resolve
```

```json
{
  "at": "2027-01-01T00:00:00Z",
  "lines": [
    {
      "line_id": "1",
      "company_product_id": "<ACETAMINOFEN>",
      "company_product_presentation_id": "<PRES_ACETA>",
      "price_list_id": "<LISTA>"
    }
  ]
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:price_list_items:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:commercial-relationship:all:read`), `ventas.test` (por `perm:commercial-relationship:all:read`), `reportes.test` (por `perm:commercial-relationship:price_list_items:read`), `consulta.test` (por `perm:commercial-relationship:price_list_items:read`)
- ❌ **No pueden (responde `403`):** `inventario.test` — no tiene ningún permiso sobre `price_list_items` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- Con lista explícita y sin precio de la presentación tampoco hay precio: `NO_PRICE_IN_LIST`.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "line_id": "1",
      "resolution": "NO_PRICE_IN_LIST",
      "unit_price": null
    }
  ]
}
```

## 3. Resolver en 2099: precio nuevo

```http
POST /api/v1/companies/<EMPRESA>/applicable-prices/resolve
```

```json
{
  "at": "2099-06-01T00:00:00Z",
  "lines": [
    {
      "line_id": "1",
      "company_product_id": "<IRBESARTAN>",
      "company_product_presentation_id": "<PRES_IRBE>"
    }
  ]
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:price_list_items:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:commercial-relationship:all:read`), `ventas.test` (por `perm:commercial-relationship:all:read`), `reportes.test` (por `perm:commercial-relationship:price_list_items:read`), `consulta.test` (por `perm:commercial-relationship:price_list_items:read`)
- ❌ **No pueden (responde `403`):** `inventario.test` — no tiene ningún permiso sobre `price_list_items` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- La consulta con un instante resuelve con los precios vigentes en ese instante; el precio histórico se conserva (SC-009).

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "resolution": "PRICE_LIST_ITEM",
      "unit_price": "31500.00"
    }
  ]
}
```

---

[← Paso anterior](04-cambiar-precio.md) · [Orden del ejercicio](ORDEN.md)
