# Paso 06 de 07 — Consultar, inactivar y reactivar

Ejercicio 1 — Adopción de productos del Excel · [← Paso anterior](05-precio-y-moneda.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](07-resumen-de-empresas.md)

**Objetivo:** Ver el listado, la consulta por lotes y el ciclo de vida.

**Necesita (de pasos anteriores):** `<EMPRESA>`, `<CP_ACETAMINOFEN>`, `<CP_WINNY>` — pasos [01](01-consultar-datos-base.md), [02](02-adoptar-acetaminofen.md), [04](04-rechazos.md)

---

## 1. Listar los productos de la empresa

```http
GET /api/v1/companies/<EMPRESA>/company-products?search=0005
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_products:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:commercial-relationship:all:read`), `ventas.test` (por `perm:commercial-relationship:all:read`), `reportes.test` (por `perm:commercial-relationship:company_products:read`), `consulta.test` (por `perm:commercial-relationship:company_products:read`)
- ❌ **No pueden (responde `403`):** `inventario.test` — no tiene ningún permiso sobre `company_products` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- Búsqueda parcial por código interno, referencia o nombre; sin `status` solo `ACTIVE`.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "internal_code": "000537",
      "display_name": "AGUJA 18GX1 1/2 CAJAX100 RFZC18B RYMCO",
      "status": "ACTIVE"
    }
  ],
  "total_records": 1
}
```

## 2. Consultar varios productos por lotes

```http
POST /api/v1/company-products/batch-lookup
```

```json
{
  "ids": [
    "<CP_ACETAMINOFEN>",
    "<CP_WINNY>",
    "00000000-0000-4000-8000-000000000000"
  ]
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_products:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:commercial-relationship:all:read`), `ventas.test` (por `perm:commercial-relationship:all:read`), `reportes.test` (por `perm:commercial-relationship:company_products:read`), `consulta.test` (por `perm:commercial-relationship:company_products:read`)
- ❌ **No pueden (responde `403`):** `inventario.test` — no tiene ningún permiso sobre `company_products` de `commercial-relationship`

**Por qué se hace así**

- Contrato para Inventory, Purchase y Sales: de 1 a 100 `id`; los inexistentes vuelven con `found: false`, sin error.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "id": "<CP_ACETAMINOFEN>",
      "found": true,
      "internal_code": "000045",
      "is_sellable": true
    },
    {
      "id": "<CP_WINNY>",
      "found": true,
      "internal_code": "015721",
      "is_sellable": true
    },
    {
      "id": "<id generado>",
      "found": false,
      "internal_code": null,
      "is_sellable": null
    }
  ]
}
```

## 3. Inactivar el acetaminofén

```http
POST /api/v1/company-products/<CP_ACETAMINOFEN>/deactivate
```

```json
{
  "version": 1
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_products:delete`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`)
- ❌ **No pueden (responde `403`):** `supervisor.test` — sobre `company_products` solo tiene `create`, `read`, `update`; le falta `delete`; `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `company_products` solo tienen `read`; les falta `delete`; `inventario.test` — no tiene ningún permiso sobre `company_products` de `commercial-relationship`
- ℹ️ Inactivar exige `delete` aunque no borra nada; reactivar exige `update`. `supervisor.test` no tiene `delete`.
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- Inactivar exige `delete` aunque no borra nada; deja de ser apto para operaciones nuevas.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "id": "<CP_ACETAMINOFEN>",
  "status": "INACTIVE",
  "version": 2
}
```

## 4. Reactivar el acetaminofén

```http
POST /api/v1/company-products/<CP_ACETAMINOFEN>/reactivate
```

```json
{
  "version": 2
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `company_products` solo tienen `read`; les falta `update`; `inventario.test` — no tiene ningún permiso sobre `company_products` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- Reactivar exige `update`; comprueba que el producto global siga `ACTIVE`, sin volver a exigir completitud ni registrar el primer uso.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "id": "<CP_ACETAMINOFEN>",
  "status": "ACTIVE",
  "version": 3
}
```

---

[← Paso anterior](05-precio-y-moneda.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](07-resumen-de-empresas.md)
