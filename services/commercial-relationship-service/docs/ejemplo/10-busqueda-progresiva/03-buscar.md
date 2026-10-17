# Paso 03 de 05 — Buscar por nombre, código y SKU

Ejercicio 10 — Búsqueda progresiva de productos y presentaciones por productos · [← Paso anterior](02-adoptar-productos.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](04-continuar.md)

**Objetivo:** Encontrar productos por partes del nombre, por código exacto y por el SKU de una presentación.

**Necesita (de pasos anteriores):** `<EMPRESA>` — pasos [01](01-consultar-datos.md)

---

## 1. Buscar «tableta» en el nombre

```http
POST /api/v1/companies/<EMPRESA>/company-products/search
```

```json
{
  "search": "tableta",
  "limit": 10
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_products:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:commercial-relationship:company_products:read`), `ventas.test` (por `perm:commercial-relationship:company_products:read`), `inventario.test` (por `perm:commercial-relationship:company_products:read`), `reportes.test` (por `perm:commercial-relationship:company_products:read`), `consulta.test` (por `perm:commercial-relationship:company_products:read`)
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- `search` busca sin distinguir mayúsculas en nombre, códigos y SKU. Dos productos tienen «TABLETA» en el nombre: vuelven en orden de `display_name`.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "id": "<ACETAMINOFEN>",
      "internal_code": "000045",
      "display_name": "ACETAMINOFEN (ADOREM) 500MG TABLETA CAJAX100 SIEGFRIED",
      "position": {
        "k": [
          "ACETAMINOFEN (ADOREM) 500MG TABLETA CAJAX100 SIEGFRIED"
        ],
        "id": "<ACETAMINOFEN>"
      }
    },
    {
      "id": "<IRBESARTAN>",
      "internal_code": "022315",
      "display_name": "IRBESARTAN+HIDROCLOROTIAZIDA (IRBESARTAN/HCT) 150+12.5MG TABLETA CAJAX30MK",
      "position": {
        "k": [
          "IRBESARTAN+HIDROCLOROTIAZIDA (IRBESARTAN/HCT) 150+12.5MG TABLETA CAJAX30MK"
        ],
        "id": "<IRBESARTAN>"
      }
    }
  ],
  "has_more": false
}
```

## 2. Buscar por una parte del SKU

```http
POST /api/v1/companies/<EMPRESA>/company-products/search
```

```json
{
  "search": "ace-",
  "limit": 10
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_products:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:commercial-relationship:company_products:read`), `ventas.test` (por `perm:commercial-relationship:company_products:read`), `inventario.test` (por `perm:commercial-relationship:company_products:read`), `reportes.test` (por `perm:commercial-relationship:company_products:read`), `consulta.test` (por `perm:commercial-relationship:company_products:read`)
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- Las dos presentaciones del acetaminofén coinciden, pero el producto aparece **una sola** vez.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "id": "<ACETAMINOFEN>",
      "internal_code": "000045",
      "display_name": "ACETAMINOFEN (ADOREM) 500MG TABLETA CAJAX100 SIEGFRIED",
      "position": {
        "k": [
          "ACETAMINOFEN (ADOREM) 500MG TABLETA CAJAX100 SIEGFRIED"
        ],
        "id": "<ACETAMINOFEN>"
      }
    }
  ],
  "has_more": false
}
```

## 3. Buscar por código interno exacto

```http
POST /api/v1/companies/<EMPRESA>/company-products/search
```

```json
{
  "internal_code": "000537",
  "limit": 10
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_products:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:commercial-relationship:company_products:read`), `ventas.test` (por `perm:commercial-relationship:company_products:read`), `inventario.test` (por `perm:commercial-relationship:company_products:read`), `reportes.test` (por `perm:commercial-relationship:company_products:read`), `consulta.test` (por `perm:commercial-relationship:company_products:read`)
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- `internal_code` y `sku` son coincidencias exactas (sin distinguir mayúsculas), no parciales.

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

---

[← Paso anterior](02-adoptar-productos.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](04-continuar.md)
