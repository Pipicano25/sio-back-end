# Parámetro `global_product_presentation_id`

[← Parámetros](README.md) · [← Índice](../index.md) · Servicio propietario: [Product Catalog](../servicios/product-catalog.md)

| Propiedad | Valor |
|---|---|
| Qué representa | Una **presentación del catálogo global** (por ejemplo, caja por 100 tabletas o unidad): la forma en que un producto global se compra o se vende. La empresa la **adopta** para obtener su [presentación empresarial](company-product-presentation-id.md), que es la que usan Ventas, Compras e Inventario |
| Nombre en las rutas y cuerpos | `global_product_presentation_id` en Commercial Relationship (cuerpo de adopción y filtro) y en las respuestas de Product Inventory Query; `presentation_id` en las rutas de Product Catalog (`/presentations/{presentation_id}`) |
| Tipo | UUID (texto) |
| Obligatorio | Sí al adoptar una presentación en una empresa |
| Ejemplo (ficticio) | `8a9b0c1d-2e3f-4a4b-9c5d-6e7f8a9b0c1d` |
| Quién lo genera | Product Catalog, al crear la presentación del producto (`id` de la respuesta `201`) |
| Alcance | Global: cualquier usuario con el permiso de lectura la ve, sin membresía |

## Cómo obtenerlo

**¿Qué hace?** Devuelve, **sin paginación**, las presentaciones definidas en el catálogo global para un producto, ordenadas por `display_order` y código. Sin `status` devuelve todas. Sirve para elegir qué presentación adopta la empresa y para mostrar el nombre y la cantidad de una presentación empresarial, que no viajan en Commercial Relationship. Ficha técnica: [Product Catalog 67](../servicios/product-catalog.md#67-get-productsproduct_idpresentations); guía principal: [Productos y precios, API 5](../principales/productos-y-precios.md#5-consultar-las-presentaciones-globales-de-un-producto).

| | |
|---|---|
| Método y ruta | `GET /api/v1/products/{product_id}/presentations` |
| URL completa | `https://sio-product-catalog-dev.onrender.com/api/v1/products/{product_id}/presentations` |
| Parámetros de ruta | `product_id` (UUID del producto global) — [cómo obtenerlo](global-product-id.md) |
| Parámetros de consulta | `status` (`ACTIVE` o `INACTIVE`; sin valor devuelve todas) |
| Permiso | `perm:product-catalog:products:read` |
| Clasificación | `READ` |

```bash
curl -X GET \
  'https://sio-product-catalog-dev.onrender.com/api/v1/products/f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72/presentations?status=ACTIVE' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

Respuesta `200` (arreglo de `PresentationResponse`, sin paginación; valores ilustrativos):

```json
[
  {
    "id": "8a9b0c1d-2e3f-4a4b-9c5d-6e7f8a9b0c1d",
    "version": 1,
    "created_at": "2026-10-19T15:04:05Z",
    "updated_at": "2026-10-19T15:04:05Z",
    "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
    "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
    "status": "ACTIVE",
    "global_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
    "code": "CJ100",
    "name": "Caja x 100 tabletas",
    "packaging_type_id": "e2f3a4b5-c6d7-4e8f-9a0b-1c2d3e4f5a6b",
    "base_quantity": "100",
    "content_quantity": null,
    "content_unit_id": null,
    "display_order": 1,
    "is_base": false,
    "first_used_at": null,
    "first_use_source": null,
    "eligible_for_adoption": true
  }
]
```

**Campo exacto:** `[].id`. Solo se adoptan presentaciones con `eligible_for_adoption: true`. `is_base` marca la presentación base (una vigente por producto, con `base_quantity` 1), `base_quantity` cuántas unidades base contiene y `code` su código en mayúsculas.

Si ya se conoce la presentación empresarial, su campo `global_product_presentation_id` lo devuelve la [API 12 de Productos y precios](../principales/productos-y-precios.md#12-consultar-las-presentaciones-de-la-empresa) o `GET https://sio-commercial-relationship-dev.onrender.com/api/v1/company-product-presentations/{presentation_id}` ([Commercial Relationship 30](../servicios/commercial-relationship.md#30-get-company-product-presentationspresentation_id)).

**Posibles errores de esta API:**

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `401` | `{"detail": "Se requiere un token de acceso Bearer"}` | Token ausente, vencido o inválido | Renovar la sesión y reintentar; si falla, volver al login |
| `403` | `PRODUCT_CATALOG.FORBIDDEN` | Falta `perm:product-catalog:products:read` | Mostrar que faltan permisos y el `trace_id` |
| `404` | `PRODUCT_CATALOG.NOT_FOUND` | El producto global no existe | Volver a buscarlo ([global_product_id](global-product-id.md)) |
| `400` | `PRODUCT_CATALOG.MALFORMED_REQUEST` | `product_id` no es UUID o `status` fuera de la enumeración | Corregir la solicitud |
| `503` | `PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | La base de datos no responde (`dependency` lo indica) | Reintentar más tarde |

## Si la presentación no existe todavía (operación `WRITE`)

**¿Qué hace la API de creación?** Agrega una presentación al producto global. El `code` se normaliza a mayúsculas y es único por producto. Solo puede haber una presentación base vigente, con `base_quantity` 1. Registra `CREATE_PRODUCT_PRESENTATION` en Audit. Ficha técnica: [Product Catalog 68](../servicios/product-catalog.md#68-post-productsproduct_idpresentations); guía principal: [Productos y precios, API 6](../principales/productos-y-precios.md#6-crear-una-presentación-global).

| | |
|---|---|
| Método y ruta | `POST /api/v1/products/{product_id}/presentations` |
| URL completa | `https://sio-product-catalog-dev.onrender.com/api/v1/products/{product_id}/presentations` |
| Permiso | `perm:product-catalog:products:update` |
| Clasificación | `WRITE` (catálogo compartido) |

Cuerpo (modelo `PresentationCreate`; no admite campos adicionales):

| Campo | Tipo | Obligatorio | Validación / valor por defecto |
|---|---|---|---|
| `code` | string | Sí | 1 a 60 caracteres efectivos; único por producto |
| `name` | string | Sí | 1 a 160 caracteres efectivos |
| `packaging_type_id` | UUID \| null | No | Tipo de empaque `ACTIVE` |
| `base_quantity` | decimal > 0 | No | `1`; debe ser `1` si `is_base` es `true` |
| `content_quantity` | decimal > 0 \| null | No | Obligatorio junto con `content_unit_id` |
| `content_unit_id` | UUID \| null | No | Unidad `ACTIVE`; obligatoria junto con `content_quantity` |
| `display_order` | integer 0–32767 | No | `0` |
| `is_base` | boolean | No | `false` |

```bash
curl -X POST \
  'https://sio-product-catalog-dev.onrender.com/api/v1/products/f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72/presentations' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "code": "CJ100",
    "name": "Caja x 100 tabletas",
    "packaging_type_id": "e2f3a4b5-c6d7-4e8f-9a0b-1c2d3e4f5a6b",
    "base_quantity": "100",
    "content_quantity": null,
    "content_unit_id": null,
    "display_order": 1,
    "is_base": false
  }'
```

La respuesta `201` devuelve `PresentationResponse` con cabecera `Location: /api/v1/presentations/{id}`. **Campo exacto:** `id`, que es el `global_product_presentation_id`.

**Posibles errores al crear:**

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `401` | `{"detail": "Se requiere un token de acceso Bearer"}` | Token ausente, vencido o inválido | Renovar la sesión y reintentar; si falla, volver al login |
| `403` | `PRODUCT_CATALOG.FORBIDDEN` | Falta `perm:product-catalog:products:update` | Mostrar que faltan permisos y el `trace_id` |
| `404` | `PRODUCT_CATALOG.NOT_FOUND` | El producto no existe | Volver a buscarlo |
| `409` | `PRODUCT_CATALOG.DUPLICATE_CODE` | El producto ya tiene una presentación con ese código | Pedir otro código |
| `409` | `PRODUCT_CATALOG.BASE_PRESENTATION_EXISTS` | Ya hay una presentación base vigente | Enviar `is_base: false` |
| `422` | `PRODUCT_CATALOG.BASE_QUANTITY_MUST_BE_ONE` | `is_base: true` con `base_quantity` distinto de 1 | Corregir la cantidad |
| `422` | `PRODUCT_CATALOG.REFERENCE_NOT_FOUND` / `REFERENCE_INACTIVE` | El tipo de empaque o la unidad de contenido no existen o están inactivos | Volver a cargar los selectores |
| `422` | `PRODUCT_CATALOG.PRODUCT_INACTIVE` | El producto está `INACTIVE` | Informar |
| `422` | `PRODUCT_CATALOG.VALIDATION_ERROR` | Código o nombre vacíos o largos, `base_quantity` ≤ 0, contenido sin unidad, campo desconocido | Corregir el formulario; `errors[]` trae `field` |
| `400` | `PRODUCT_CATALOG.MALFORMED_REQUEST` | `product_id` no es UUID o el cuerpo no es JSON | Error de programación del cliente |
| `503` | `PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` | La base de datos no responde | Reintentar más tarde; nada se guardó |

## Cómo usarlo después

- Adoptarla en la empresa: campo `global_product_presentation_id` del cuerpo de la [API 11 de Productos y precios](../principales/productos-y-precios.md#11-adoptar-una-presentación-en-la-empresa), junto con el [company_product_id](company-product-id.md) del mismo producto global; devuelve el [company_product_presentation_id](company-product-presentation-id.md).
- Saber si la empresa ya la adoptó: filtro `?global_product_presentation_id=` de la [API 12](../principales/productos-y-precios.md#12-consultar-las-presentaciones-de-la-empresa) con `status=ALL`.
- Asociarle un código de barras: campo `global_product_presentation_id` del cuerpo de la [API 7](../principales/productos-y-precios.md#7-registrar-un-código-de-barras-del-producto-global).

## Errores frecuentes

| Respuesta | Causa probable |
|---|---|
| `404 PRODUCT_CATALOG.NOT_FOUND` | El producto o la presentación no existe |
| `409 COMMERCIAL_RELATIONSHIP.DUPLICATE_PRESENTATION_ADOPTION` al adoptar | La presentación global ya está adoptada para ese producto empresarial (activa o inactiva) |
| `422 COMMERCIAL_RELATIONSHIP.GLOBAL_PRESENTATION_OF_OTHER_PRODUCT` al adoptar | La presentación pertenece a otro producto global |
| `422 COMMERCIAL_RELATIONSHIP.GLOBAL_PRESENTATION_NOT_ELIGIBLE` al adoptar | La presentación o su producto no son adoptables |
