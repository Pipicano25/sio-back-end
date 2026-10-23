# Paso 14 de 14 — Consultar el producto por lotes y por filtros (spec 022)

Ejercicio 5 — Cepillo Colgate infantil pack x 2 (producto inactivo) · [← Paso anterior](13-verificar-producto-inactivo.md) · [Orden del ejercicio](ORDEN.md)

**Objetivo:** Ver el resumen del catálogo de un lote de productos y buscar productos por marca, para consumidores como el servicio de consultas consolidadas.

**Necesita (de pasos anteriores):** `<PRODUCTO>`, `<PRES_PACK_X2>`, `<MARCA_COLGATE>` — pasos [02](02-crear-marca.md), [06](06-crear-producto.md), [08](08-crear-presentacion.md)

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
- Las imágenes **no** vienen en este resumen: pertenecen a las presentaciones y se consultan por presentación (`POST /presentations/batch-lookup`, siguiente llamada).

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
      "identifiers": []
    }
  ]
}
```

## 2. Imagen de la presentación por lotes

```http
POST /api/v1/presentations/batch-lookup?include_images=true
```

```json
{
  "ids": [
    "<PRES_PACK_X2>"
  ]
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:product-catalog:all:read`), `ventas.test` (por `perm:product-catalog:all:read`), `inventario.test` (por `perm:product-catalog:all:read`), `reportes.test` (por `perm:product-catalog:products:read`), `consulta.test` (por `perm:product-catalog:products:read`)

**Por qué se hace así**

- Cada presentación trae su imagen principal: `has_image`, `image_asset_id` e `image_url`.
- Con `include_images=true` agrega `images[]` con todas sus imágenes `ACTIVE`, la principal primero.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "code": "PACK_X2",
      "has_image": true,
      "image_asset_id": "<ACTIVO_IMAGEN_2>",
      "images": [
        {
          "is_primary": true
        },
        {
          "is_primary": false
        }
      ]
    }
  ]
}
```

## 3. Productos de la marca, incluidos los inactivos

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

## 4. ¿El cepillo tiene alguna presentación con imagen?

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

- Modo evaluador: devuelve los candidatos que cumplen. `has_image: true` significa "al menos una presentación con imagen principal `ACTIVE`": es solo una condición de búsqueda.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "ids": [
    "<PRODUCTO>"
  ]
}
```

---

[← Paso anterior](13-verificar-producto-inactivo.md) · [Orden del ejercicio](ORDEN.md)
