# Paso 04 de 07 — Rechazos de la adopción

Ejercicio 1 — Adopción de productos del Excel · [← Paso anterior](03-adoptar-aguja.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](05-precio-y-moneda.md)

**Objetivo:** Ver los errores de elegibilidad y de unicidad.

**Necesita (de pasos anteriores):** `<EMPRESA>`, `<GP_ACETAMINOFEN>`, `<GP_CEPILLO>`, `<GP_INCOMPLETO>`, `<GP_WINNY>` — pasos [01](01-consultar-datos-base.md)

**Deja guardado para los siguientes pasos:** `<CP_WINNY>`

---

## 1. Adoptar otra vez el acetaminofén (rechazado)

```http
POST /api/v1/companies/<EMPRESA>/company-products
```

```json
{
  "global_product_id": "<GP_ACETAMINOFEN>",
  "internal_code": "000045-B",
  "display_name": "Duplicado",
  "currency_code": "COP"
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_products:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `company_products` solo tienen `read`; les falta `create`
- ℹ️ Adoptar no exige permisos en Product Catalog al usuario: la elegibilidad y el registro de primer uso los hace el servicio con su propia identidad técnica (cliente `commercial-relationship-service`).
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- Una empresa adopta cada producto global **una sola vez**, aunque la adopción esté inactiva (en ese caso se reactiva): `409 DUPLICATE_ADOPTION`. No se llama a Product Catalog.

**Respuesta esperada (error) — `409 Conflict`** (abreviada)

```json
{
  "status": 409,
  "code": "COMMERCIAL_RELATIONSHIP.DUPLICATE_ADOPTION",
  "detail": "La empresa ya adoptó este producto global; si está inactivo, reactívelo.",
  "errors": [
    {
      "field": "global_product_id",
      "message": "La empresa ya adoptó este producto global; si está inactivo, reactívelo.",
      "code": "DUPLICATE_ADOPTION"
    }
  ]
}
```

## 2. Adoptar el cepillo inactivo (rechazado)

```http
POST /api/v1/companies/<EMPRESA>/company-products
```

```json
{
  "global_product_id": "<GP_CEPILLO>",
  "internal_code": "022348",
  "display_name": "CEPILLO COLGATE INFANTIL 2-5 AÑOS EXTRA SUAVE NIÑA PACK X2",
  "currency_code": "COP",
  "lot_tracking_enabled": true
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_products:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `company_products` solo tienen `read`; les falta `create`
- ℹ️ Adoptar no exige permisos en Product Catalog al usuario: la elegibilidad y el registro de primer uso los hace el servicio con su propia identidad técnica (cliente `commercial-relationship-service`).
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- La fila 16610 tiene `Estado = I`: el producto global está `INACTIVE` y no admite nuevas adopciones: `422 GLOBAL_PRODUCT_INACTIVE`.

**Respuesta esperada (error) — `422 Unprocessable Content`** (abreviada)

```json
{
  "status": 422,
  "code": "COMMERCIAL_RELATIONSHIP.GLOBAL_PRODUCT_INACTIVE",
  "detail": "El producto global indicado está inactivo en Product Catalog.",
  "errors": [
    {
      "field": "global_product_id",
      "message": "El producto global indicado está inactivo en Product Catalog.",
      "code": "GLOBAL_PRODUCT_INACTIVE"
    }
  ]
}
```

## 3. Adoptar un producto incompleto (rechazado)

```http
POST /api/v1/companies/<EMPRESA>/company-products
```

```json
{
  "global_product_id": "<GP_INCOMPLETO>",
  "internal_code": "FICT-01",
  "display_name": "Producto incompleto (ficticio)",
  "currency_code": "COP"
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_products:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `company_products` solo tienen `read`; les falta `create`
- ℹ️ Adoptar no exige permisos en Product Catalog al usuario: la elegibilidad y el registro de primer uso los hace el servicio con su propia identidad técnica (cliente `commercial-relationship-service`).
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- Solo se adopta un producto **completo** (elegible). Como no es elegible, no se registra el primer uso ni se guarda nada: `422 GLOBAL_PRODUCT_NOT_ELIGIBLE`.

**Respuesta esperada (error) — `422 Unprocessable Content`** (abreviada)

```json
{
  "status": 422,
  "code": "COMMERCIAL_RELATIONSHIP.GLOBAL_PRODUCT_NOT_ELIGIBLE",
  "detail": "El producto global no está completo y no se puede adoptar.",
  "errors": [
    {
      "field": "global_product_id",
      "message": "El producto global no está completo y no se puede adoptar.",
      "code": "GLOBAL_PRODUCT_NOT_ELIGIBLE"
    }
  ]
}
```

## 4. Adoptar los pañales con un código ya usado (rechazado)

```http
POST /api/v1/companies/<EMPRESA>/company-products
```

```json
{
  "global_product_id": "<GP_WINNY>",
  "internal_code": "000045",
  "display_name": "WINNY GOLD ETAPA 6 XXXG PAQUETEX30 TECNOQUIMICAS",
  "currency_code": "COP"
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_products:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `company_products` solo tienen `read`; les falta `create`
- ℹ️ Adoptar no exige permisos en Product Catalog al usuario: la elegibilidad y el registro de primer uso los hace el servicio con su propia identidad técnica (cliente `commercial-relationship-service`).
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- `internal_code` es único en la empresa (sin distinguir mayúsculas): 000045 ya es del acetaminofén: `409 DUPLICATE_INTERNAL_CODE`.

**Respuesta esperada (error) — `409 Conflict`** (abreviada)

```json
{
  "status": 409,
  "code": "COMMERCIAL_RELATIONSHIP.DUPLICATE_INTERNAL_CODE",
  "detail": "Ya existe un registro con ese código interno en la empresa.",
  "errors": [
    {
      "field": "internal_code",
      "message": "Ya existe un registro con ese código interno en la empresa.",
      "code": "DUPLICATE_INTERNAL_CODE"
    }
  ]
}
```

## 5. Adoptar los pañales con su código del Excel

```http
POST /api/v1/companies/<EMPRESA>/company-products
```

```json
{
  "global_product_id": "<GP_WINNY>",
  "internal_code": "015721",
  "reference_code": "74865",
  "display_name": "WINNY GOLD ETAPA 6 XXXG PAQUETEX30 TECNOQUIMICAS",
  "currency_code": "COP"
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_products:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `company_products` solo tienen `read`; les falta `create`
- ℹ️ Adoptar no exige permisos en Product Catalog al usuario: la elegibilidad y el registro de primer uso los hace el servicio con su propia identidad técnica (cliente `commercial-relationship-service`).
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- Con el `Código` 015721 de la fila 11499 la adopción procede.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<CP_WINNY>",
  "internal_code": "015721",
  "status": "ACTIVE"
}
```

**Guardar:** `id` → `<CP_WINNY>`

---

[← Paso anterior](03-adoptar-aguja.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](05-precio-y-moneda.md)
