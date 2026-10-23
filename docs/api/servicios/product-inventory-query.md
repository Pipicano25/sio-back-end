# Product Inventory Query API

[← Índice](../index.md) · [Autenticación](../guias/autenticacion.md) · [Permisos](../guias/permisos.md) · [Errores](../guias/errores.md) · [Parámetros](../parametros/README.md)

## Introducción

Product Inventory Query es el servicio de **consulta consolidada** para las pantallas de productos y existencias. En una sola llamada devuelve el producto empresarial con su catálogo, presentaciones (con su imagen), precio por presentación y existencias por sucursal, combinando Commercial Relationship, Product Catalog e Inventory. Es la forma recomendada de construir buscadores de productos, puntos de venta y tableros de inventario sin encadenar llamadas desde el navegador.

## Responsabilidad

- Autorizar primero el alcance con Operational Context (membresía `ACTIVE` y sucursales de la empresa) y después consultar los servicios propietarios.
- Devolver solo los **bloques** que el token permite ver: precios, existencias y mínimos se omiten (o se devuelven `null`) cuando falta el permiso correspondiente, sin fallar la consulta.
- Paginar por cursor, con límite de trabajo por solicitud, y nunca devolver resultados parciales sin avisarlo.
- Solo lectura: no tiene base de datos propia ni operaciones de escritura.

## Datos del servicio

| Campo | Valor |
|---|---|
| URL base | `https://sio-product-inventory-query-dev.onrender.com/api/v1` |
| Salud | `https://sio-product-inventory-query-dev.onrender.com/health/live`, `/health/ready` |
| Swagger / OpenAPI | [/docs](https://sio-product-inventory-query-dev.onrender.com/docs) · [/openapi.json](https://sio-product-inventory-query-dev.onrender.com/openapi.json) |
| Formato de error | Problem Details con `code` `PRODUCT_INVENTORY_QUERY.*` y `trace_id` |
| Operaciones en el contrato desplegado | 10 (8 consultas + 2 de salud) |
| Verificación | OpenAPI de Render del 2026-10-19 cruzado con `services/product-inventory-query-service` |

## Autenticación y permisos

Todas las rutas salvo `/health/*` exigen `Authorization: Bearer <ACCESS_TOKEN>`.

### Permiso funcional de cada consulta

| Consulta | Permiso | Grupos de la plantilla que lo tienen |
|---|---|---|
| Productos (`product-overviews`) | `perm:product-inventory-query:product_overviews:read` | `administradores`, `supervisores`, `ventas`, `inventario` |
| Existencias (`inventory-overviews`) | `perm:product-inventory-query:inventory_overviews:read` | `administradores`, `supervisores`, `ventas`, `inventario` |
| Bajo mínimo (`low-stock-products`) | `perm:product-inventory-query:low_stock_products:read` **más** `perm:product-inventory-query:stock:read` y `perm:inventory:product-policies:read` | `administradores`, `supervisores`, `inventario` |
| Resumen (`inventory-summary`) | `perm:product-inventory-query:inventory_summary:read` | `administradores`, `supervisores`, `inventario` |

### Bloques opcionales de la respuesta

| Bloque | Permiso que lo habilita | Qué aparece | Filtros que lo exigen |
|---|---|---|---|
| Precios | `perm:commercial-relationship:price_list_items:read` | `presentations[].price` | `price_list_id` no produce `403`, pero sin el permiso no se devuelve precio |
| Existencias | `perm:product-inventory-query:stock:read` | `stock` (total, por sucursal y equivalencias) | `stock_state` |
| Mínimos | `perm:inventory:product-policies:read` | `stock.branches[].minimum_stock` y `minimum_state` | `minimum_state` |

Sin el permiso de un bloque, el campo se omite o es `null` y la consulta responde `200`. Usar un **filtro** de un bloque no autorizado produce `403 PRODUCT_INVENTORY_QUERY.FORBIDDEN`. El grupo `ventas` ve precios y existencias pero no mínimos; `inventario` ve existencias y mínimos pero no precios (según la plantilla del realm).

## Alcance de datos

| Regla | Detalle |
|---|---|
| Empresa | Membresía `ACTIVE` del usuario en `company_id`; si no, o si la empresa no existe, `404 PRODUCT_INVENTORY_QUERY.NOT_FOUND` |
| Sucursales | Con membresía, **cualquier sucursal de la empresa** es consultable (no se exige asignación). En rutas de empresa: `scope=COMPANY` (por defecto, todas las sucursales activas) o `branch_id` repetible (máx. 100), excluyentes entre sí. En rutas por sucursal: `branch_id` en la ruta; si es de otra empresa, `404`; `branch_id` o `scope` por consulta producen `422` |
| Datos globales | Nombres canónicos, marcas, categorías, identificadores e imagen provienen del catálogo global (Product Catalog) |

## Paginación por cursor

Las seis consultas de listado (productos, existencias y bajo mínimo, por empresa y por sucursal) paginan por cursor, **sin totales**:

| Campo de la respuesta | Significado |
|---|---|
| `items[]` | Hasta `page_size` elementos (1 a 20; por defecto 20) |
| `has_next` | Hay más resultados |
| `next_cursor` | Cursor opaco (máx. 2048 caracteres) para la página siguiente; enviar como `cursor=` **con los mismos filtros, orden y `page_size`** |
| `pagination_reset` | `true` si el servicio ignoró el cursor y reinició desde la primera página |
| `pagination_reset_reason` | `FILTERS_CHANGED`, `SORT_CHANGED`, `PAGE_SIZE_CHANGED` o `CURSOR_EXPIRED` (los cursores caducan a los 900 s) |
| `partial` | `true` si la página se cortó por el límite de trabajo del servidor (5 s) antes de llenarse; **no es el final**: continúe con `next_cursor` |
| `partial_reason` | `WORK_LIMIT_REACHED` |
| `sort_applied` | Orden efectivamente aplicado, por ejemplo `display_name:asc` |
| `resolved_at` | Instante de resolución de la consulta |

Un cursor manipulado o ilegible produce `422 PRODUCT_INVENTORY_QUERY.INVALID_CURSOR` («El cursor no es válido. Repita la consulta…»).

Orden predeterminado en productos y existencias: `display_name:asc` sin filtros o con `search`, `internal_code` o `sku`; `canonical_name:asc` con `barcode`, `identifier` o filtros de catálogo (`brand_id`, `category_id`, `product_type`); `company_product_id:asc` con solo `stock_state=IN_STOCK` o `minimum_state`. En bajo mínimo: `shortfall:desc`. Un `sort` explícito (`display_name`, `internal_code` o `created_at`, con `:asc` o `:desc`) se aplica tal cual.

## Filtros comunes de los listados

| Parámetro | Tipo | Validación | Significado |
|---|---|---|---|
| `search` | string | máx. 200 | Texto en el nombre, `internal_code`, `reference_code` o SKU de presentación |
| `internal_code` | string | máx. 60 | Código interno exacto, sin distinguir mayúsculas |
| `sku` | string | máx. 80 | SKU de presentación exacto |
| `barcode` | string | máx. 120 | Código de barras exacto (Product Catalog) |
| `identifier` | string | máx. 120 | Identificador global exacto (Product Catalog) |
| `brand_id` | UUID, repetible | máx. 100 | Marca (varias con O) |
| `category_id` | UUID, repetible | máx. 100 | Categoría (varias con O); con `include_descendants=true` incluye subcategorías |
| `status` | `ACTIVE` \| `INACTIVE` \| `ALL` | por defecto `ACTIVE` | Estado del producto empresarial |
| `product_type` | string | máx. 20 | Tipo de producto de Product Catalog |
| `has_image` | boolean | — | Con o sin imagen principal apta (spec 024: al menos una presentación con imagen principal; ver [Imágenes por presentación](#imágenes-por-presentación-spec-024-pendiente-de-despliegue)) |
| `stock_state` | `IN_STOCK` \| `OUT_OF_STOCK` | exige bloque existencias | No disponible en bajo mínimo |
| `minimum_state` | `NO_POLICY` \| `BELOW_MINIMUM` \| `AT_MINIMUM` \| `ABOVE_MINIMUM` | exige bloque mínimos | Solo en existencias |
| `price_list_id` | UUID | — | Solo en productos: lista de precios; sin ella, la predeterminada que aplique Commercial Relationship |
| `sort`, `page_size`, `cursor` | — | ver arriba | — |

Un parámetro desconocido produce `422 VALIDATION_ERROR`.

## Imágenes por presentación (spec 024; pendiente de despliegue)

> **Estado:** implementado en el código y validado por las pruebas del servicio el 2026-10-23; **aún no desplegado en Render**. Las fichas de abajo describen el contrato desplegado. Al desplegar la spec 024 (después de Product Catalog), las respuestas cambian así:

| Dónde | Antes (contrato desplegado) | Con la spec 024 |
|---|---|---|
| Producto (`ProductOverview`, `InventoryOverview`) | `has_image`, `asset_id`, `image_url` del producto | **Se retiran**: la imagen es de cada presentación |
| `presentations[]` | Sin campos de imagen | `has_image` (la presentación tiene imagen principal `ACTIVE`), `asset_id` e `image_url` (URL pública firmada de la principal, o `null`) |
| `presentations[].images` | — | Solo con `include_images=true`: todas las imágenes `ACTIVE` (`asset_id`, `image_url`, `is_primary`), la principal primero; `[]` si no tiene. Sin el parámetro, el campo se omite |
| Bajo mínimo (`LowStockPair`) | `has_image`, `asset_id`, `image_url` | **Se retiran**: no trae imágenes. `include_images` en esta consulta → `422` |
| Filtro `has_image` | Con o sin imagen principal del producto | Condición de búsqueda: `true` = al menos una presentación con imagen principal `ACTIVE`; `false` = ninguna. No significa que "el producto tenga imagen" |

Parámetro nuevo en productos y existencias (empresa y sucursal):

| Parámetro | Tipo | Por defecto | Significado |
|---|---|---|---|
| `include_images` | boolean | `false` | Agrega `presentations[].images`. No forma parte de la huella del cursor: se puede activar o desactivar entre páginas sin reiniciar la paginación. No agrega llamadas a Product Catalog (usa la misma consulta por lotes de presentaciones) |

Ejemplo de solicitud:

```bash
curl -sS 'https://sio-product-inventory-query-dev.onrender.com/api/v1/companies/9b2f7c3e-1d4a-4e8b-9c6f-2a1b3c4d5e6f/product-overviews?search=Acetaminof%C3%A9n&include_images=true' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Fragmento de una presentación en la respuesta (valores ilustrativos):

```json
{
  "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
  "global_product_presentation_id": "c6c7d8e9-f0a1-4b2c-9d3e-4f5a6b7c8d94",
  "code": "UN",
  "name": "Unidad",
  "sku": "7701234567890",
  "internal_code": "PRD-0001-U",
  "status": "ACTIVE",
  "is_sellable": true,
  "base_quantity_factor": "1.0000",
  "has_image": true,
  "asset_id": "4c8291aa-edb7-46e7-8e38-83d456610944",
  "image_url": "https://sio-product-catalog-dev.onrender.com/api/v1/public/product-images?ref=<referencia firmada>",
  "images": [
    {"asset_id": "4c8291aa-edb7-46e7-8e38-83d456610944", "image_url": "https://sio-product-catalog-dev.onrender.com/api/v1/public/product-images?ref=<referencia firmada>", "is_primary": true}
  ]
}
```

Para cargar o cambiar imágenes, el frontend usa Product Catalog con `global_product_id` y `global_product_presentation_id` de esta respuesta ([imágenes por presentación](product-catalog.md#imágenes-por-presentación-spec-024-operaciones-i-1-a-i-8)). Ejemplos ejecutados: `services/product-inventory-query-service/docs/ejemplo/1-catalogo-con-imagen-y-precio/` (pasos 1 a 3).

## Tabla de endpoints

| # | Método | Ruta relativa | Descripción | Permiso | Clase | Ficha |
|---|---|---|---|---|---|---|
| 1 | `GET` | `/health/live` (sin prefijo) | Proceso vivo | Ninguno | `READ` | [Ver](#1-get-healthlive) |
| 2 | `GET` | `/health/ready` (sin prefijo) | Preparado | Ninguno | `READ` | [Ver](#2-get-healthready) |
| 3 | `GET` | `/companies/{company_id}/product-overviews` | Productos con presentaciones, precios, imagen y existencias | `perm:product-inventory-query:product_overviews:read` | `READ` | [Ver](#3-get-companiescompany_idproduct-overviews) |
| 4 | `GET` | `/companies/{company_id}/branches/{branch_id}/product-overviews` | Ídem, existencias de una sucursal | ídem | `READ` | [Ver](#4-get-companiescompany_idbranchesbranch_idproduct-overviews) |
| 5 | `GET` | `/companies/{company_id}/inventory-overviews` | Existencias por producto, sucursal y empresa | `perm:product-inventory-query:inventory_overviews:read` | `READ` | [Ver](#5-get-companiescompany_idinventory-overviews) |
| 6 | `GET` | `/companies/{company_id}/branches/{branch_id}/inventory-overviews` | Ídem, una sucursal | ídem | `READ` | [Ver](#6-get-companiescompany_idbranchesbranch_idinventory-overviews) |
| 7 | `GET` | `/companies/{company_id}/low-stock-products` | Pares producto–sucursal bajo el mínimo | `perm:product-inventory-query:low_stock_products:read` (+ stock y mínimos) | `READ` | [Ver](#7-get-companiescompany_idlow-stock-products) |
| 8 | `GET` | `/companies/{company_id}/branches/{branch_id}/low-stock-products` | Ídem, una sucursal | ídem | `READ` | [Ver](#8-get-companiescompany_idbranchesbranch_idlow-stock-products) |
| 9 | `GET` | `/companies/{company_id}/inventory-summary` | Indicadores operativos por sucursal y consolidados | `perm:product-inventory-query:inventory_summary:read` | `READ` | [Ver](#9-get-companiescompany_idinventory-summary) |
| 10 | `GET` | `/companies/{company_id}/branches/{branch_id}/inventory-summary` | Ídem, una sucursal | ídem | `READ` | [Ver](#10-get-companiescompany_idbranchesbranch_idinventory-summary) |

## Operaciones

### 1. `GET /health/live`

`READ`, sin autenticación. `https://sio-product-inventory-query-dev.onrender.com/health/live` → `200` `{"status": "ok"}`.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-product-inventory-query-dev.onrender.com/health/live'
```

### 2. `GET /health/ready`

`READ`, sin autenticación. `https://sio-product-inventory-query-dev.onrender.com/health/ready` → `200` `{"status": "ok"}`; `503` si la configuración o el JWKS no están disponibles. No tiene base de datos.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-product-inventory-query-dev.onrender.com/health/ready'
```

### 3. `GET /companies/{company_id}/product-overviews`

| | |
|---|---|
| Clasificación | `READ` |
| URL | `https://sio-product-inventory-query-dev.onrender.com/api/v1/companies/{company_id}/product-overviews` |
| Permiso | `perm:product-inventory-query:product_overviews:read` (+ bloques según permisos) |
| Alcance | Empresa; `scope=COMPANY` (por defecto) o `branch_id` repetible |

Parámetros: `company_id` (ruta, [cómo obtenerlo](../parametros/company-id.md)); `branch_id` (query, repetible, [cómo obtenerlo](../parametros/branch-id.md)) o `scope=COMPANY`; los filtros comunes, `price_list_id`, `sort`, `page_size`, `cursor`.

```bash
curl -sS 'https://sio-product-inventory-query-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/product-overviews?search=acetaminofen&status=ACTIVE&page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Respuesta `200` (`CursorPage[ProductOverview]`; valores ilustrativos; token con los tres bloques):

```json
{
  "items": [
    {
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "global_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
      "display_name": "Acetaminofén 500 mg",
      "canonical_name": "Acetaminofén 500 mg tableta",
      "internal_code": "PRD-0001",
      "reference_code": null,
      "status": "ACTIVE",
      "global_status": "ACTIVE",
      "product_type": "GOOD",
      "brand": {"id": "b1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e", "code": "GEN", "name": "Genérico"},
      "categories": [
        {"id": "c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f", "code": "ANALG", "name": "Analgésicos", "is_primary": true}
      ],
      "identifiers": [
        {"type": "EAN13", "value": "7701234567890", "is_primary": true, "global_product_presentation_id": "c6c7d8e9-f0a1-4b2c-9d3e-4f5a6b7c8d94"}
      ],
      "base_unit": {"id": "d1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e", "code": "UN", "name": "Unidad"},
      "has_image": true,
      "image_url": "https://sio-product-catalog-dev.onrender.com/public/product-images/firma-ilustrativa",
      "presentations": [
        {
          "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
          "global_product_presentation_id": "c6c7d8e9-f0a1-4b2c-9d3e-4f5a6b7c8d94",
          "code": "UN",
          "name": "Unidad",
          "sku": "7701234567890",
          "internal_code": "PRD-0001-U",
          "status": "ACTIVE",
          "is_sellable": true,
          "base_quantity_factor": "1.0000",
          "price": {
            "price_list_id": "5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b",
            "price_list_item_id": "6f7a8b9c-0d1e-4f2a-9b3c-4d5e6f7a8b9c",
            "unit_price": "800.00",
            "currency_code": "COP",
            "resolution": "PRICE_LIST_ITEM"
          }
        }
      ],
      "stock": {
        "base_unit": {"id": "d1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e", "code": "UN", "name": "Unidad"},
        "total_base_quantity": "800.0000",
        "branches": [
          {
            "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
            "base_quantity": "800.0000",
            "balance_state": "REGISTERED",
            "minimum_stock": "100.0000",
            "minimum_state": "ABOVE_MINIMUM"
          }
        ],
        "equivalences": [
          {"company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83", "whole_units": 800, "remainder_base_quantity": "0.0000"}
        ]
      }
    }
  ],
  "page_size": 20,
  "has_next": false,
  "next_cursor": null,
  "pagination_reset": false,
  "pagination_reset_reason": null,
  "partial": false,
  "partial_reason": null,
  "sort_applied": "display_name:asc",
  "resolved_at": "2026-10-19T15:40:00Z"
}
```

Campos destacados de `ProductOverview`:

| Campo | Significado |
|---|---|
| `company_product_id`, `global_product_id` | Identificadores para [ventas y compras](../parametros/company-product-id.md) y para el catálogo global |
| `status` / `global_status` | Estado del producto empresarial y del global |
| `identifiers[]` | Códigos de barras u otros identificadores globales (`type`, `value`, `is_primary`, presentación asociada) |
| `image_url` | URL de la imagen principal construida por Product Catalog (referencia firmada; se copia tal cual). `null` si `has_image` es `false`. El ejemplo es ilustrativo. Spec 024: pasa a cada presentación ([ver](#imágenes-por-presentación-spec-024-pendiente-de-despliegue)) |
| `presentations[].base_quantity_factor` | Unidades base por presentación, 4 decimales |
| `presentations[].price.resolution` | `PRICE_LIST_ITEM` (precio encontrado), `NO_PRICE_IN_LIST`, `NO_APPLICABLE_PRICE_LIST` o `PRICE_LIST_NOT_APPLICABLE`, tal como los informa Commercial Relationship; `unit_price` es `null` salvo en el primero |
| `stock.branches[].balance_state` | `REGISTERED` (hay saldo registrado, aunque sea cero) o `NOT_REGISTERED` |
| `stock.branches[].minimum_state` | `NO_POLICY`, `BELOW_MINIMUM`, `AT_MINIMUM`, `ABOVE_MINIMUM` |
| `stock.equivalences[]` | Cuántas unidades enteras de cada presentación caben en el total y el resto en unidad base |

Errores: `403 FORBIDDEN` (sin permiso funcional o filtro de bloque no autorizado), `404 NOT_FOUND` (empresa sin membresía o `branch_id` de otra empresa), `422 VALIDATION_ERROR` / `INVALID_CURSOR`, `503 DEPENDENCY_UNAVAILABLE` (una dependencia no respondió en 3 s por llamada u 8 s en total, o respondió algo inválido; nunca hay resultados parciales sin `partial: true`).

Dependencias: Operational Context (autorización), Commercial Relationship (productos, presentaciones, precios), Product Catalog (catálogo, identificadores, imagen), Inventory (existencias y mínimos). Las llamadas a los propietarios usan la identidad técnica del servicio, por lo que los bloques dependen de los permisos **del usuario** evaluados por este servicio.

### 4. `GET /companies/{company_id}/branches/{branch_id}/product-overviews`

Igual que la operación 3, pero `stock` contiene **solo la sucursal de la ruta** (`stock.branches` de un elemento y `total_base_quantity` de esa sucursal). `branch_id` en la ruta debe ser de la empresa (`404` si no); no se admiten `branch_id` ni `scope` por consulta (`422`). Mismos filtros, bloques, paginación y respuesta.

URL: `https://sio-product-inventory-query-dev.onrender.com/api/v1/companies/{company_id}/branches/{branch_id}/product-overviews`.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-product-inventory-query-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/branches/7c9e6679-7425-40de-944b-e07fc1f90ae7/product-overviews?page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`CursorPage_ProductOverview_`; valores ilustrativos):

```json
{
  "items": [
    {
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "global_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
      "display_name": "Acetaminofén 500 mg tableta",
      "canonical_name": "Acetaminofén 500 mg tableta",
      "internal_code": "PRD-0001",
      "reference_code": "REF-0001",
      "status": "ACTIVE",
      "global_status": "ACTIVE",
      "product_type": "GOOD",
      "brand": {
        "id": "b1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e",
        "code": "GENFAR",
        "name": "Genfar"
      },
      "categories": [
        {
          "id": "3af5ffc6-f94e-4d7e-8271-b22e87afa664",
          "code": "ANALGESICOS",
          "name": "Analgésicos",
          "is_primary": true
        }
      ],
      "identifiers": [
        {
          "type": "GTIN",
          "value": "7702001234567",
          "is_primary": true,
          "global_product_presentation_id": "8a9b0c1d-2e3f-4a4b-9c5d-6e7f8a9b0c1d"
        }
      ],
      "base_unit": {
        "id": "d1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e",
        "code": "UN",
        "name": "Unidad"
      },
      "has_image": false,
      "image_url": null,
      "presentations": [
        {
          "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
          "global_product_presentation_id": "8a9b0c1d-2e3f-4a4b-9c5d-6e7f8a9b0c1d",
          "code": "CJ100",
          "name": "Caja x 100",
          "sku": "ACET-500-CJ100",
          "internal_code": "PRD-0001-CJ100",
          "status": "ACTIVE",
          "is_sellable": true,
          "base_quantity_factor": "1",
          "price": null
        }
      ],
      "stock": null
    }
  ],
  "page_size": 20,
  "has_next": false,
  "next_cursor": null,
  "pagination_reset": false,
  "pagination_reset_reason": null,
  "partial": false,
  "partial_reason": null,
  "sort_applied": "display_name:asc",
  "resolved_at": "2026-10-19T15:04:05Z"
}
```

### 5. `GET /companies/{company_id}/inventory-overviews`

| | |
|---|---|
| Clasificación | `READ` |
| URL | `https://sio-product-inventory-query-dev.onrender.com/api/v1/companies/{company_id}/inventory-overviews` |
| Permiso | `perm:product-inventory-query:inventory_overviews:read` (+ bloques existencias y mínimos) |
| Alcance | Empresa; `scope=COMPANY` o `branch_id` repetible |

Devuelve los productos **con control de inventario** y sus existencias en unidad base, por sucursal y consolidadas, con equivalencias por presentación y, con el permiso de mínimos, el estado frente al mínimo. Parámetros: los filtros comunes más `minimum_state`; **no** admite `price_list_id` y las presentaciones **no** traen `price`.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-product-inventory-query-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/inventory-overviews?page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Respuesta `200` (`CursorPage[InventoryOverview]`): mismo objeto que `ProductOverview` sin el bloque de precios. Ejemplo de un elemento con bloque de mínimos:

```json
{
  "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
  "global_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
  "display_name": "Acetaminofén 500 mg",
  "canonical_name": "Acetaminofén 500 mg tableta",
  "internal_code": "PRD-0001",
  "reference_code": null,
  "status": "ACTIVE",
  "global_status": "ACTIVE",
  "product_type": "GOOD",
  "brand": null,
  "categories": [],
  "identifiers": [],
  "base_unit": {"id": "d1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e", "code": "UN", "name": "Unidad"},
  "has_image": false,
  "image_url": null,
  "presentations": [
    {
      "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
      "global_product_presentation_id": "c6c7d8e9-f0a1-4b2c-9d3e-4f5a6b7c8d94",
      "code": "CJ100",
      "name": "Caja x 100",
      "sku": null,
      "internal_code": "PRD-0001-C",
      "status": "ACTIVE",
      "is_sellable": true,
      "base_quantity_factor": "100.0000"
    }
  ],
  "stock": {
    "base_unit": {"id": "d1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e", "code": "UN", "name": "Unidad"},
    "total_base_quantity": "250.0000",
    "branches": [
      {"branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7", "base_quantity": "250.0000", "balance_state": "REGISTERED", "minimum_stock": "300.0000", "minimum_state": "BELOW_MINIMUM"},
      {"branch_id": "9b2f5c1d-3e4a-4f6b-8c7d-2a1b3c4d5e6f", "base_quantity": "0.0000", "balance_state": "NOT_REGISTERED", "minimum_stock": null, "minimum_state": "NO_POLICY"}
    ],
    "equivalences": [
      {"company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83", "whole_units": 2, "remainder_base_quantity": "50.0000"}
    ]
  }
}
```

Errores y dependencias como en la operación 3 (sin Commercial Relationship para precios).

### 6. `GET /companies/{company_id}/branches/{branch_id}/inventory-overviews`

Igual que la operación 5 para la sucursal de la ruta (`stock` solo de esa sucursal). `branch_id`/`scope` por consulta → `422`; sucursal de otra empresa → `404`.

URL: `https://sio-product-inventory-query-dev.onrender.com/api/v1/companies/{company_id}/branches/{branch_id}/inventory-overviews`.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-product-inventory-query-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/branches/7c9e6679-7425-40de-944b-e07fc1f90ae7/inventory-overviews?page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`CursorPage_InventoryOverview_`; valores ilustrativos):

```json
{
  "items": [
    {
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "global_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
      "display_name": "Acetaminofén 500 mg tableta",
      "canonical_name": "Acetaminofén 500 mg tableta",
      "internal_code": "PRD-0001",
      "reference_code": "REF-0001",
      "status": "ACTIVE",
      "global_status": "ACTIVE",
      "product_type": "GOOD",
      "brand": {
        "id": "b1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e",
        "code": "GENFAR",
        "name": "Genfar"
      },
      "categories": [
        {
          "id": "3af5ffc6-f94e-4d7e-8271-b22e87afa664",
          "code": "ANALGESICOS",
          "name": "Analgésicos",
          "is_primary": true
        }
      ],
      "identifiers": [
        {
          "type": "GTIN",
          "value": "7702001234567",
          "is_primary": true,
          "global_product_presentation_id": "8a9b0c1d-2e3f-4a4b-9c5d-6e7f8a9b0c1d"
        }
      ],
      "base_unit": {
        "id": "d1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e",
        "code": "UN",
        "name": "Unidad"
      },
      "has_image": false,
      "image_url": null,
      "presentations": [
        {
          "company_product_presentation_id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
          "global_product_presentation_id": "8a9b0c1d-2e3f-4a4b-9c5d-6e7f8a9b0c1d",
          "code": "CJ100",
          "name": "Caja x 100",
          "sku": "ACET-500-CJ100",
          "internal_code": "PRD-0001-CJ100",
          "status": "ACTIVE",
          "is_sellable": true,
          "base_quantity_factor": "1"
        }
      ],
      "stock": null
    }
  ],
  "page_size": 20,
  "has_next": false,
  "next_cursor": null,
  "pagination_reset": false,
  "pagination_reset_reason": null,
  "partial": false,
  "partial_reason": null,
  "sort_applied": "display_name:asc",
  "resolved_at": "2026-10-19T15:04:05Z"
}
```

### 7. `GET /companies/{company_id}/low-stock-products`

| | |
|---|---|
| Clasificación | `READ` |
| URL | `https://sio-product-inventory-query-dev.onrender.com/api/v1/companies/{company_id}/low-stock-products` |
| Permisos | `perm:product-inventory-query:low_stock_products:read` **y** `perm:product-inventory-query:stock:read` **y** `perm:inventory:product-policies:read`; sin los tres, `403` |
| Alcance | Empresa; `scope=COMPANY` o `branch_id` repetible |

Devuelve pares (producto, sucursal) con **política de mínimo activa** y existencia **estrictamente menor** que el mínimo. Parámetros: filtros comunes salvo `stock_state`, `minimum_state` y `price_list_id`; `sort`, `page_size`, `cursor`. Orden predeterminado `shortfall:desc` (mayor faltante primero).

```bash
curl -sS 'https://sio-product-inventory-query-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/low-stock-products?page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Respuesta `200` (`CursorPage[LowStockPair]`; valores ilustrativos):

```json
{
  "items": [
    {
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "display_name": "Acetaminofén 500 mg",
      "internal_code": "PRD-0001",
      "base_unit": {"id": "d1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e", "code": "UN", "name": "Unidad"},
      "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "base_quantity": "250.0000",
      "minimum_stock": "300.0000",
      "shortfall": "50.0000",
      "policy_status": "ACTIVE",
      "has_image": false,
      "image_url": null
    }
  ],
  "page_size": 20,
  "has_next": false,
  "next_cursor": null,
  "pagination_reset": false,
  "pagination_reset_reason": null,
  "partial": false,
  "partial_reason": null,
  "sort_applied": "shortfall:desc",
  "resolved_at": "2026-10-19T15:40:00Z"
}
```

`shortfall` = `minimum_stock − base_quantity`, siempre mayor que cero. Un producto con política pero existencia igual al mínimo **no** aparece.

### 8. `GET /companies/{company_id}/branches/{branch_id}/low-stock-products`

Igual que la operación 7 para la sucursal de la ruta. `branch_id`/`scope` por consulta → `422`.

URL: `https://sio-product-inventory-query-dev.onrender.com/api/v1/companies/{company_id}/branches/{branch_id}/low-stock-products`.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-product-inventory-query-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/branches/7c9e6679-7425-40de-944b-e07fc1f90ae7/low-stock-products?page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`CursorPage_LowStockPair_`; valores ilustrativos):

```json
{
  "items": [
    {
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "display_name": "Acetaminofén 500 mg tableta",
      "internal_code": "PRD-0001",
      "base_unit": {
        "id": "d1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e",
        "code": "UN",
        "name": "Unidad"
      },
      "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "base_quantity": "2.0000",
      "minimum_stock": "10",
      "shortfall": "0.0000",
      "policy_status": "ACTIVE",
      "has_image": false,
      "image_url": null
    }
  ],
  "page_size": 20,
  "has_next": false,
  "next_cursor": null,
  "pagination_reset": false,
  "pagination_reset_reason": null,
  "partial": false,
  "partial_reason": null,
  "sort_applied": "display_name:asc",
  "resolved_at": "2026-10-19T15:04:05Z"
}
```

### 9. `GET /companies/{company_id}/inventory-summary`

| | |
|---|---|
| Clasificación | `READ` |
| URL | `https://sio-product-inventory-query-dev.onrender.com/api/v1/companies/{company_id}/inventory-summary` |
| Permiso | `perm:product-inventory-query:inventory_summary:read` |
| Parámetros | `company_id` (ruta); `branch_id` (query, repetible, máx. 100) **o** `scope=COMPANY` (por defecto) |

Sin paginación. 

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-product-inventory-query-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/inventory-summary' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```
Respuesta `200` (`InventorySummaryOut`; valores ilustrativos):

```json
{
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "resolved_at": "2026-10-19T15:40:00Z",
  "adopted_products": 320,
  "branches": [
    {
      "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "products_with_positive_balance": 280,
      "products_with_zero_balance": 15,
      "products_with_policy": 120,
      "products_below_minimum": 9
    }
  ],
  "consolidated": {
    "products_with_positive_balance": 280,
    "products_with_zero_balance": 15,
    "products_with_policy": 120,
    "products_below_minimum": 9
  }
}
```

Reglas: `adopted_products` son los productos `ACTIVE` con control de inventario según Commercial Relationship, **solo a nivel de empresa**. Los indicadores por sucursal y consolidados vienen de Inventory: un producto sin registro de saldo no cuenta en ninguno; pueden incluir productos inactivos o sin control de inventario que conservan saldo. Resumen **solo operativo**: sin costos ni valoración.

### 10. `GET /companies/{company_id}/branches/{branch_id}/inventory-summary`

Igual que la operación 9 para la sucursal de la ruta: `branches` tiene solo esa sucursal y `consolidated` coincide con ella; `adopted_products` sigue siendo de la empresa. `branch_id`/`scope` por consulta → `422`; sucursal de otra empresa → `404`.

URL: `https://sio-product-inventory-query-dev.onrender.com/api/v1/companies/{company_id}/branches/{branch_id}/inventory-summary`.

Ejemplo de solicitud (sin cuerpo):

```bash
curl -sS 'https://sio-product-inventory-query-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/branches/7c9e6679-7425-40de-944b-e07fc1f90ae7/inventory-summary' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ejemplo de respuesta `200` (`InventorySummaryOut`; valores ilustrativos):

```json
{
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "resolved_at": "2026-10-19T15:04:05Z",
  "adopted_products": 12,
  "branches": [
    {
      "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "products_with_positive_balance": 9,
      "products_with_zero_balance": 1,
      "products_with_policy": 10,
      "products_below_minimum": 1
    }
  ],
  "consolidated": {
    "products_with_positive_balance": 9,
    "products_with_zero_balance": 1,
    "products_with_policy": 10,
    "products_below_minimum": 1
  }
}
```

## Errores frecuentes

| Respuesta | Causa | Qué hacer |
|---|---|---|
| `403 PRODUCT_INVENTORY_QUERY.FORBIDDEN` | Falta el permiso funcional, o se usó `stock_state`/`minimum_state` sin el bloque, o faltan los permisos adicionales de bajo mínimo | No ofrecer esos filtros a perfiles sin el bloque |
| `404 PRODUCT_INVENTORY_QUERY.NOT_FOUND` | Sin membresía `ACTIVE`, empresa inexistente o `branch_id` de otra empresa | Revisar `/me/operational-context` |
| `422 PRODUCT_INVENTORY_QUERY.INVALID_CURSOR` | Cursor alterado o de otra consulta | Repetir sin `cursor` |
| `422 VALIDATION_ERROR` | Parámetro desconocido, `branch_id` junto con `scope`, `page_size` fuera de 1–20, `branch_id`/`scope` en rutas de sucursal | Corregir la consulta |
| `pagination_reset: true` en `200` | Cambiaron filtros/orden/`page_size` o el cursor venció (900 s) | Descartar las páginas anteriores y reiniciar la lista |
| `partial: true` en `200` | Límite de trabajo alcanzado (5 s) | Seguir pidiendo con `next_cursor`; no es el final |
| `503 PRODUCT_INVENTORY_QUERY.DEPENDENCY_UNAVAILABLE` | Un servicio no respondió a tiempo | Reintentar |

## Dependencias

| Servicio | Uso |
|---|---|
| Operational Context | Membresía y sucursales de la empresa, antes de cualquier otra llamada |
| Commercial Relationship | Productos empresariales, presentaciones, búsqueda, precios por lista, conteo de adoptados |
| Product Catalog | Datos globales (nombre canónico, marca, categorías, identificadores, tipo, unidad base, imagen) |
| Inventory | Existencias por sucursal, políticas de mínimo e indicadores |

## Cobertura

| Verificación | Resultado |
|---|---|
| Operaciones en el OpenAPI desplegado | 10 |
| Operaciones documentadas | 10 |
| Permisos contrastados con el código | Sí (`api/product_overviews.py`, `inventory_overviews.py`, `low_stock_products.py`, `inventory_summary.py`, `visibility.py`) |
| Esquemas contrastados | Sí (OpenAPI desplegado, modelos `CursorPage`, `ProductOverview`, `InventoryOverview`, `LowStockPair`, `InventorySummaryOut`) |
| Pendiente | Valores exactos de `product_type`, `identifiers[].type` y formato de `image_url` (los define Product Catalog; ver su ficha). Despliegue en Render de la spec 024 (imágenes por presentación e `include_images`) |
