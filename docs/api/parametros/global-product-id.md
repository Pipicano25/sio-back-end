# Parámetro `global_product_id`

[← Parámetros](README.md) · [← Índice](../index.md) · Servicio propietario: [Product Catalog](../servicios/product-catalog.md)

| Propiedad | Valor |
|---|---|
| Qué representa | Un **producto del catálogo global** de SIO, compartido por todas las empresas (nombre canónico, marca, unidad base, categorías, presentaciones globales y códigos de barras). Una empresa lo **adopta** para obtener su [producto empresarial](company-product-id.md) |
| Nombre en las rutas y cuerpos | `global_product_id` en Commercial Relationship (cuerpo de adopción y filtro) y en Product Inventory Query; `product_id` en las rutas de Product Catalog (`/products/{product_id}`) |
| Tipo | UUID (texto) |
| Obligatorio | Sí al adoptar un producto en una empresa; opcional como filtro |
| Ejemplo (ficticio) | `f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72` |
| Quién lo genera | Product Catalog, al crear el producto global (`id` de la respuesta `201`) |
| Alcance | Global: cualquier usuario con el permiso de lectura lo ve, sin membresía |

## Cómo obtenerlo

**¿Qué hace?** Busca, con paginación, productos del catálogo global por nombre, código de barras, marca, categoría, fabricante, grupo o atributos. Sin `status` devuelve productos de cualquier estado. Cada producto indica si es adoptable (`eligible_for_adoption`). Ficha técnica: [Product Catalog 49](../servicios/product-catalog.md#49-get-products); guía principal: [Productos y precios, API 1](../principales/productos-y-precios.md#1-buscar-productos-globales).

| | |
|---|---|
| Método y ruta | `GET /api/v1/products` |
| URL completa | `https://sio-product-catalog-dev.onrender.com/api/v1/products` |
| Parámetros de consulta | `page` (≥1), `page_size` (1–100, por defecto 20), `search` (máx. 200), `identifier` (máx. 120; código de barras u otro identificador exacto), `status` (`ACTIVE` o `INACTIVE`), `brand_id`, `category_id` (UUID) con `include_descendants` (boolean, por defecto `false`), `manufacturer_organization_id`, `group_id` (UUID), `attribute_filters` (repetible, formato `CODIGO:valor`) |
| Permiso | `perm:product-catalog:products:read` |
| Clasificación | `READ` |

```bash
curl -X GET \
  'https://sio-product-catalog-dev.onrender.com/api/v1/products?search=acetaminofen&status=ACTIVE&page=1&page_size=20' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

Respuesta `200` (modelo `PaginatedResponse[ProductResponse]`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
      "version": 3,
      "created_at": "2026-10-19T15:04:05Z",
      "updated_at": "2026-10-19T15:04:05Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "status": "ACTIVE",
      "product_type": "GOOD",
      "canonical_name": "Acetaminofén 500 mg tableta",
      "description": null,
      "global_brand_id": "b1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e",
      "manufacturer_organization_id": null,
      "base_unit_id": "d1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e",
      "first_used_at": "2026-10-19T15:04:05Z",
      "first_use_source": "ADOPTION",
      "completeness": {
        "is_complete": true,
        "issues": [],
        "missing_attribute_definition_ids": [],
        "out_of_classification_value_ids": []
      },
      "eligible_for_adoption": true,
      "warnings": [],
      "detail": null
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

**Campo exacto:** `items[].id`. Solo se adoptan productos con `eligible_for_adoption: true`. Si es `false`, `completeness.issues[]` indica qué falta (categoría, presentación o atributos obligatorios). `canonical_name` es el texto para mostrar.

Otras formas de localizarlo, documentadas en la ficha del servicio: `GET https://sio-product-catalog-dev.onrender.com/api/v1/products/by-identifier/{value}` por código de barras ([Product Catalog 52](../servicios/product-catalog.md#52-get-productsby-identifiervalue)) y `POST https://sio-product-catalog-dev.onrender.com/api/v1/products/batch-lookup` para varios UUID a la vez ([Product Catalog 51](../servicios/product-catalog.md#51-post-productsbatch-lookup)). Desde un producto empresarial, el campo `global_product_id` de la [API 10](../principales/productos-y-precios.md#10-consultar-un-producto-de-la-empresa) lo devuelve.

**Posibles errores de esta API:**

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `401` | `{"detail": "Se requiere un token de acceso Bearer"}` | Token ausente, vencido o inválido | Renovar la sesión y reintentar; si falla, volver al login |
| `403` | `PRODUCT_CATALOG.FORBIDDEN` | Falta `perm:product-catalog:products:read` | Mostrar que faltan permisos y el `trace_id` |
| `400` | `PRODUCT_CATALOG.MALFORMED_REQUEST` | `search` > 200, `identifier` > 120, `status` fuera de la enumeración, UUID o booleano inválido, paginación fuera de rango | Corregir los filtros; `errors[]` trae `field` |
| `422` | `PRODUCT_CATALOG.VALIDATION_ERROR` | `attribute_filters` sin el formato `CODIGO:valor` o con un atributo no filtrable | Corregir el filtro de atributos |
| `503` | `PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | La base de datos no responde (`dependency` lo indica) | Reintentar más tarde |

## Si el producto global no existe todavía (operación `WRITE`)

Busca antes por nombre y por `identifier` para no duplicarlo: si otra empresa ya lo creó, se reutiliza su `id`.

**¿Qué hace la API de creación?** Da de alta el producto en el catálogo global, disponible para todas las empresas. Valida que la marca y la unidad base existan y estén `ACTIVE`, y el fabricante en Party Identity si se envía. Si ya existe otro producto con el mismo nombre normalizado y la misma marca **no** falla: lo crea y devuelve la advertencia `POSSIBLE_DUPLICATE` en `warnings[]`. El producto nace **no adoptable** hasta asignarle categoría y presentación. Ficha técnica: [Product Catalog 50](../servicios/product-catalog.md#50-post-products); guía principal: [Productos y precios, API 3](../principales/productos-y-precios.md#3-crear-un-producto-global).

| | |
|---|---|
| Método y ruta | `POST /api/v1/products` |
| URL completa | `https://sio-product-catalog-dev.onrender.com/api/v1/products` |
| Permiso | `perm:product-catalog:products:create` |
| Clasificación | `WRITE` (catálogo compartido; normalmente lo hacen administradores o supervisores) |

Cuerpo (modelo `ProductCreate`; no admite campos adicionales):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `product_type` | `"GOOD"` | Sí | Único valor admitido |
| `canonical_name` | string | Sí | 1 a 200 caracteres efectivos; se recortan y unen espacios |
| `description` | string \| null | No | — |
| `global_brand_id` | UUID \| null | No | Marca `ACTIVE` del catálogo |
| `manufacturer_organization_id` | UUID \| null | No | Organización existente en Party Identity |
| `base_unit_id` | UUID | Sí | Unidad de medida `ACTIVE` |

```bash
curl -X POST \
  'https://sio-product-catalog-dev.onrender.com/api/v1/products' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "product_type": "GOOD",
    "canonical_name": "Acetaminofén 500 mg tableta",
    "description": null,
    "global_brand_id": "b1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e",
    "manufacturer_organization_id": null,
    "base_unit_id": "d1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e"
  }'
```

La respuesta `201` devuelve `ProductResponse` con cabecera `Location: /api/v1/products/{id}`. **Campo exacto:** `id`, que es el `global_product_id`. Mientras `eligible_for_adoption` sea `false` hay que completar la [API 4](../principales/productos-y-precios.md#4-asignar-una-categoría-al-producto-global) y la [API 6](../principales/productos-y-precios.md#6-crear-una-presentación-global).

**Posibles errores al crear:**

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `401` | `{"detail": "Se requiere un token de acceso Bearer"}` | Token ausente, vencido o inválido | Renovar la sesión y reintentar; si falla, volver al login |
| `403` | `PRODUCT_CATALOG.FORBIDDEN` | Falta `perm:product-catalog:products:create` | Mostrar que faltan permisos y el `trace_id` |
| `403` | `PRODUCT_CATALOG.MANUFACTURER_ACCESS_DENIED` | El usuario no puede consultar organizaciones en Party Identity | Pedir `perm:party-identity:organization_identities:read` o no enviar fabricante |
| `422` | `PRODUCT_CATALOG.REFERENCE_NOT_FOUND` / `REFERENCE_INACTIVE` | La marca o la unidad base no existen o están inactivas | Volver a cargar el selector |
| `422` | `PRODUCT_CATALOG.MANUFACTURER_NOT_FOUND` | El fabricante no existe en Party Identity | Volver a buscar la organización |
| `422` | `PRODUCT_CATALOG.VALIDATION_ERROR` | `product_type` distinto de `GOOD`, nombre vacío o > 200, UUID inválido, campo obligatorio ausente o desconocido | Corregir el formulario; `errors[]` trae `field` |
| `400` | `PRODUCT_CATALOG.MALFORMED_REQUEST` | El cuerpo no es JSON válido | Error de programación del cliente |
| `503` | `PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | Party Identity o la base de datos no responden | Reintentar más tarde; nada se guardó |

## Cómo usarlo después

- Adoptarlo en la empresa: campo `global_product_id` del cuerpo de la [API 8 de Productos y precios](../principales/productos-y-precios.md#8-adoptar-un-producto-global-en-la-empresa); devuelve el [company_product_id](company-product-id.md).
- Completarlo en el catálogo: `{product_id}` de la ruta de la [API 4](../principales/productos-y-precios.md#4-asignar-una-categoría-al-producto-global) (categoría), la [API 6](../principales/productos-y-precios.md#6-crear-una-presentación-global) (presentación) y la [API 7](../principales/productos-y-precios.md#7-registrar-un-código-de-barras-del-producto-global) (código de barras).
- Listar sus presentaciones globales: `{product_id}` de la [API 5](../principales/productos-y-precios.md#5-consultar-las-presentaciones-globales-de-un-producto) ([global_product_presentation_id](global-product-presentation-id.md)).
- Saber si la empresa ya lo adoptó: filtro `?global_product_id=` de la [API 9](../principales/productos-y-precios.md#9-buscar-y-listar-los-productos-de-la-empresa) con `status=ALL`.

## Errores frecuentes

| Respuesta | Causa probable |
|---|---|
| `404 PRODUCT_CATALOG.NOT_FOUND` | El UUID no existe en el catálogo global |
| `422 COMMERCIAL_RELATIONSHIP.GLOBAL_PRODUCT_NOT_ELIGIBLE` al adoptar | El producto no está completo (`eligible_for_adoption: false`) |
| `422 COMMERCIAL_RELATIONSHIP.GLOBAL_PRODUCT_INACTIVE` / `GLOBAL_PRODUCT_NOT_FOUND` al adoptar | El producto global está `INACTIVE` o no existe |
| `409 COMMERCIAL_RELATIONSHIP.DUPLICATE_ADOPTION` al adoptar | La empresa ya adoptó ese producto (activo o inactivo) |
