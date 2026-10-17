# Paso 04 de 05 — Continuar desde la posición del último producto

Ejercicio 10 — Búsqueda progresiva de productos y presentaciones por productos · [← Paso anterior](03-buscar.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](05-lotes-y-rechazos.md)

**Objetivo:** Pedir de a dos productos y seguir con la posición del último recibido.

**Necesita (de pasos anteriores):** `<EMPRESA>` — pasos [01](01-consultar-datos.md)

**Deja guardado para los siguientes pasos:** `<POS_K>`, `<POS_ID>`

---

## 1. Primeros dos productos

```http
POST /api/v1/companies/<EMPRESA>/company-products/search
```

```json
{
  "limit": 2
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_products:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:commercial-relationship:company_products:read`), `ventas.test` (por `perm:commercial-relationship:company_products:read`), `inventario.test` (por `perm:commercial-relationship:company_products:read`), `reportes.test` (por `perm:commercial-relationship:company_products:read`), `consulta.test` (por `perm:commercial-relationship:company_products:read`)
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- Sin filtros vuelven los productos `ACTIVE` en orden de `display_name`. `has_more = true`: quedan productos.

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
  "has_more": true
}
```

**Guardar:** `items[1].position.k[0]` → `<POS_K>` · `items[1].position.id` → `<POS_ID>`

## 2. Continuar después del segundo

```http
POST /api/v1/companies/<EMPRESA>/company-products/search
```

```json
{
  "limit": 2,
  "after": {
    "k": [
      "<POS_K>"
    ],
    "id": "<POS_ID>"
  }
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_products:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:commercial-relationship:company_products:read`), `ventas.test` (por `perm:commercial-relationship:company_products:read`), `inventario.test` (por `perm:commercial-relationship:company_products:read`), `reportes.test` (por `perm:commercial-relationship:company_products:read`), `consulta.test` (por `perm:commercial-relationship:company_products:read`)
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- `after` es la `position` del último producto usado. Vuelve solo el tercero y `has_more = false`: no hay más. Ningún producto se repite ni se salta.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
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

---

[← Paso anterior](03-buscar.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](05-lotes-y-rechazos.md)
