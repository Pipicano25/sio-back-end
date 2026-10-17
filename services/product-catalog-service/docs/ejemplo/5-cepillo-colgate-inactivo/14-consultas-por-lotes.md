# Paso 14 de 14 — Consultar el producto por lotes y por filtros (spec 022)

Ejercicio 5 — Cepillo Colgate infantil pack x 2 (producto inactivo) · [← Paso anterior](13-verificar-producto-inactivo.md) · [Orden del ejercicio](ORDEN.md)

**Objetivo:** Ver el resumen del catálogo de un lote de productos y buscar productos por marca, para consumidores como el servicio de consultas consolidadas.

**Necesita (de pasos anteriores):** `<PRODUCTO>`, `<MARCA_COLGATE>` — pasos [02](02-crear-marca.md), [06](06-crear-producto.md)

---

## 1. Resumen del producto por lotes

```http
POST /api/v1/products/summaries/batch-lookup
```

```json
{
  "ids": [
    "<PRODUCTO>"
  ]
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:product-catalog:all:read`), `ventas.test` (por `perm:product-catalog:all:read`), `inventario.test` (por `perm:product-catalog:all:read`), `reportes.test` (por `perm:product-catalog:products:read`), `consulta.test` (por `perm:product-catalog:products:read`)

**Por qué se hace así**

- Hasta 100 productos en una llamada: nombre canónico, marca, unidad base, categorías e identificadores `ACTIVE`, sin pedir cada producto por separado.
- `has_image: false`: la imagen del paso 10 es ilustrativa y no está en el almacenamiento de SIO con clave derivada de su SHA-256, así que **no es apta** para URL directa; `image_url` es `null`.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "found": true,
      "canonical_name": "Colgate cepillo dental infantil 2 a 5 años extra suave niña",
      "status": "INACTIVE",
      "brand": {
        "id": "<MARCA_COLGATE>",
        "code": "COLGATE",
        "name": "Colgate"
      },
      "base_unit": {
        "id": "<UND>",
        "code": "UND",
        "name": "Unidad"
      },
      "categories": [
        {
          "id": "<CAT_CEPILLOS>",
          "code": "CEPILLOS_DENTALES",
          "name": "Cepillos dentales",
          "is_primary": true
        }
      ],
      "identifiers": [],
      "has_image": false,
      "image_url": null
    }
  ]
}
```

## 2. Productos de la marca, incluidos los inactivos

```http
POST /api/v1/products/match
```

```json
{
  "brand_ids": [
    "<MARCA_COLGATE>"
  ],
  "status": "ALL",
  "limit": 20
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:product-catalog:all:read`), `ventas.test` (por `perm:product-catalog:all:read`), `inventario.test` (por `perm:product-catalog:all:read`), `reportes.test` (por `perm:product-catalog:products:read`), `consulta.test` (por `perm:product-catalog:products:read`)

**Por qué se hace así**

- Modo conductor: los productos que cumplen los filtros en orden de nombre canónico normalizado e `id`, de a `limit`. Cada uno trae su `position` para seguir con `after`.
- Por defecto `status` es `ACTIVE`; el cepillo está inactivo, por eso se pide `ALL`.
- No hay conteos: `has_more` dice si quedan productos.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "id": "<PRODUCTO>",
      "position": {
        "k": [
          "colgate cepillo dental infantil 2 a 5 anos extra suave nina"
        ],
        "id": "<PRODUCTO>"
      }
    }
  ],
  "has_more": false
}
```

## 3. ¿El cepillo tiene una imagen apta?

```http
POST /api/v1/products/match
```

```json
{
  "candidate_ids": [
    "<PRODUCTO>"
  ],
  "has_image": true,
  "status": "ALL"
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:product-catalog:all:read`), `ventas.test` (por `perm:product-catalog:all:read`), `inventario.test` (por `perm:product-catalog:all:read`), `reportes.test` (por `perm:product-catalog:products:read`), `consulta.test` (por `perm:product-catalog:products:read`)

**Por qué se hace así**

- Modo evaluador: devuelve los candidatos que cumplen. Ninguno: la imagen no es apta.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "ids": []
}
```

---

[← Paso anterior](13-verificar-producto-inactivo.md) · [Orden del ejercicio](ORDEN.md)
