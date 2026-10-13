# Paso 03 de 05 — Crear la lista y registrar el precio

Ejercicio 6 — Listas de precios y precio aplicable · [← Paso anterior](02-adoptar-productos.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](04-cambiar-precio.md)

**Objetivo:** Lista predeterminada en COP con el precio real y el rechazo por solapamiento.

**Necesita (de pasos anteriores):** `<EMPRESA>`, `<IRBESARTAN>`, `<PRES_IRBE>` — pasos [01](01-consultar-datos.md), [02](02-adoptar-productos.md)

**Deja guardado para los siguientes pasos:** `<LISTA>`, `<PRECIO>`

---

## 1. Crear la lista 10 como predeterminada en COP

```http
POST /api/v1/companies/<EMPRESA>/price-lists
```

```json
{
  "code": "LISTA-10",
  "name": "Precio Lista 10",
  "currency_code": "COP",
  "is_default": true
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:price_lists:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `price_lists` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `price_lists` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- Hay como máximo una lista predeterminada `ACTIVE` por empresa y moneda.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<LISTA>",
  "code": "LISTA-10",
  "name": "Precio Lista 10",
  "currency_code": "COP",
  "is_default": true,
  "status": "ACTIVE",
  "version": 1
}
```

**Guardar:** `id` → `<LISTA>`

## 2. Registrar un precio sin presentación (rechazado)

```http
POST /api/v1/companies/<EMPRESA>/price-list-items
```

```json
{
  "price_list_id": "<LISTA>",
  "company_product_id": "<IRBESARTAN>",
  "unit_price": "30420",
  "valid_from": "2026-01-01T00:00:00Z"
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:price_list_items:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `price_list_items` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `price_list_items` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- No hay precios generales por producto (spec 019): falta `company_product_presentation_id` → `422 VALIDATION_ERROR`.

**Respuesta esperada (error) — `422 Unprocessable Content`** (abreviada)

```json
{
  "status": 422,
  "code": "COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR",
  "detail": "La solicitud contiene datos inválidos.",
  "errors": [
    {
      "field": "company_product_presentation_id",
      "message": "Field required",
      "code": "VALIDATION_ERROR"
    }
  ]
}
```

## 3. Registrar el precio real de la caja x30 del irbesartán

```http
POST /api/v1/companies/<EMPRESA>/price-list-items
```

```json
{
  "price_list_id": "<LISTA>",
  "company_product_id": "<IRBESARTAN>",
  "company_product_presentation_id": "<PRES_IRBE>",
  "unit_price": "30420",
  "valid_from": "2026-01-01T00:00:00Z"
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:price_list_items:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `price_list_items` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `price_list_items` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- Precio de la presentación (por caja x30), vigente desde 2026 y sin fin. La moneda es la de la lista y admite 2 decimales.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<PRECIO>",
  "price_list_id": "<LISTA>",
  "company_product_id": "<IRBESARTAN>",
  "company_product_presentation_id": "<PRES_IRBE>",
  "unit_price": "30420.00",
  "currency_code": "COP",
  "status": "ACTIVE",
  "version": 1
}
```

**Guardar:** `id` → `<PRECIO>`

## 4. Registrar otro precio que se cruza (rechazado)

```http
POST /api/v1/companies/<EMPRESA>/price-list-items
```

```json
{
  "price_list_id": "<LISTA>",
  "company_product_id": "<IRBESARTAN>",
  "company_product_presentation_id": "<PRES_IRBE>",
  "unit_price": "31000",
  "valid_from": "2026-06-01T00:00:00Z"
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:price_list_items:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `price_list_items` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `price_list_items` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- Las vigencias de una misma lista, producto y presentación no se solapan: `409 PRICE_PERIOD_OVERLAP`.

**Respuesta esperada (error) — `409 Conflict`** (abreviada)

```json
{
  "status": 409,
  "code": "COMMERCIAL_RELATIONSHIP.PRICE_PERIOD_OVERLAP",
  "detail": "La vigencia se cruza con otro precio activo de la misma lista, producto y presentación."
}
```

---

[← Paso anterior](02-adoptar-productos.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](04-cambiar-precio.md)
