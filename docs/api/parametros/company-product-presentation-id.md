# Parámetro `company_product_presentation_id`

[← Parámetros](README.md) · [← Índice](../index.md) · Servicio propietario: [Commercial Relationship](../servicios/commercial-relationship.md)

| Propiedad | Valor |
|---|---|
| Qué representa | La **presentación empresarial** de un producto adoptado (por ejemplo «caja × 100» o «unidad»): la unidad en la que la empresa compra o vende. Cada línea de venta o compra exige el producto empresarial **y** su presentación |
| Nombre en las rutas y cuerpos | `company_product_presentation_id` |
| Tipo | UUID (texto) |
| Obligatorio | Sí en `lines[]` de ventas y compras |
| Ejemplo (ficticio) | `a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83` |
| Quién lo genera | Commercial Relationship, al adoptar la presentación global (`id` de la respuesta) |
| Alcance | Empresa |

## Cómo obtenerlo

**¿Qué hace?** Lista, con paginación, las presentaciones (unidades de venta o compra) que la empresa adoptó, filtrando normalmente por `company_product_id` para ver solo las del producto elegido, con sus banderas de compra/venta, las predeterminadas y su estado. Es la fuente de `company_product_presentation_id` para líneas de venta y compra y para precios. Ficha técnica: [Commercial Relationship 26](../servicios/commercial-relationship.md#26-get-companiescompany_idcompany-product-presentations); guía principal: [Productos y precios, API 12](../principales/productos-y-precios.md#12-consultar-las-presentaciones-de-la-empresa).

| | |
|---|---|
| Método y ruta | `GET /api/v1/companies/{company_id}/company-product-presentations` |
| URL completa | `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-product-presentations` |
| Parámetros de ruta | `company_id` (UUID) — [cómo obtenerlo](company-id.md) |
| Parámetros de consulta | `company_product_id` (UUID; **úsalo para traer solo las presentaciones del producto elegido**), `global_product_presentation_id` (UUID), `search` (máx. 100), `status` (`ACTIVE`, `INACTIVE`, `ALL`), `is_purchasable`, `is_sellable` (boolean), `page`, `page_size` (1–100, por defecto 20) |
| Permiso | `perm:commercial-relationship:company_product_presentations:read` |
| Clasificación | `READ` |

```bash
curl -X GET \
  'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/company-product-presentations?company_product_id=e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61&is_sellable=true' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

Respuesta `200` (modelo `PaginatedResponse[CompanyProductPresentationResponse]`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "a5b6c7d8-e9f0-4a1b-8c2d-3e4f5a6b7c83",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "ACTIVE",
      "version": 1,
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "created_at": "2026-02-05T08:05:00Z",
      "updated_at": "2026-02-05T08:05:00Z",
      "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "global_product_presentation_id": "8a9b0c1d-2e3f-4a4b-9c5d-6e7f8a9b0c1d",
      "internal_code": "PRD-0001-CJ",
      "sku": "7702001023456",
      "reference_code": null,
      "is_purchasable": true,
      "is_sellable": true,
      "is_default_purchase": true,
      "is_default_sale": true
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

**Campo exacto:** `items[].id`. Preselecciona la que tenga `is_default_sale: true` (ventas) o `is_default_purchase: true` (compras). El nombre y la cantidad base de la presentación («caja × 100») no están en este objeto: provienen de la presentación global (`global_product_presentation_id`) en Product Catalog, ([API 5 de Productos y precios](../principales/productos-y-precios.md#5-consultar-las-presentaciones-globales-de-un-producto)), o directamente de [Product Inventory Query](../servicios/product-inventory-query.md), que ya combina ambos. Solo las presentaciones `ACTIVE` y vendibles admiten precios y políticas de ganancia.

**Posibles errores de esta API:**

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `401` | `{"detail": "Se requiere un token de acceso Bearer"}` | Token ausente, vencido o inválido | Renovar la sesión y reintentar; si falla, volver al login |
| `403` | `COMMERCIAL_RELATIONSHIP.FORBIDDEN` | Falta `perm:commercial-relationship:company_product_presentations:read` | Mostrar que faltan permisos y el `trace_id` |
| `403` | `COMMERCIAL_RELATIONSHIP.OPERATIONAL_ACCESS_DENIED` | Operational Context rechazó la comprobación de membresía (suele faltar `perm:operational-context:application_users:read`) | Revisar los permisos del usuario |
| `404` | `COMMERCIAL_RELATIONSHIP.NOT_FOUND` | Sin membresía `ACTIVE` en la empresa, o empresa inexistente | Volver a leer el contexto operativo |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR` | Paginación fuera de rango, `search` > 100, `status` o un booleano inválido, UUID mal formado | Corregir los parámetros |
| `503` | `COMMERCIAL_RELATIONSHIP.DEPENDENCY_UNAVAILABLE` | Operational Context o la base de datos no responden (`dependency` lo indica) | Reintentar más tarde |

## Si la presentación no está adoptada todavía (operación `WRITE`)

1. Lista las presentaciones globales del producto en Product Catalog:

**¿Qué hace?** Devuelve, sin paginación, las presentaciones definidas en el catálogo global para un producto (unidad, caja, blíster…), con su cantidad base y si son elegibles para adopción. Ficha técnica: [Product Catalog 67](../servicios/product-catalog.md#67-get-productsproduct_idpresentations); guía completa: [global_product_presentation_id](global-product-presentation-id.md). Sus errores son `401` con `{"detail": "Se requiere un token de acceso Bearer"}`, `403 PRODUCT_CATALOG.FORBIDDEN` (falta `perm:product-catalog:products:read`), `404 PRODUCT_CATALOG.NOT_FOUND` si el producto no existe y `400 PRODUCT_CATALOG.MALFORMED_REQUEST` si `product_id` o `status` son inválidos.

| | |
|---|---|
| Método y ruta | `GET /api/v1/products/{product_id}/presentations` (`product_id` = [global_product_id](global-product-id.md)) |
| URL completa | `https://sio-product-catalog-dev.onrender.com/api/v1/products/{product_id}/presentations` |
| Parámetros de consulta | `status` (`ACTIVE` o `INACTIVE`; sin valor devuelve todas) |
| Permiso | `perm:product-catalog:products:read` |
| Respuesta | `200` con un **array** (sin paginación) de `PresentationResponse`: `id`, `global_product_id`, `code`, `name`, `packaging_type_id`, `base_quantity`, `content_quantity`, `content_unit_id`, `display_order`, `is_base`, `status`, `eligible_for_adoption`, … |

El `global_product_presentation_id` es el campo `id` de cada elemento.

2. Adóptala en la empresa:

**¿Qué hace la API de adopción?** Crea la presentación empresarial enlazando un producto empresarial de la empresa con una presentación global del mismo producto global, con banderas de compra/venta y predeterminadas. Devuelve `201` con la presentación; su `id` es el `company_product_presentation_id`. Si se marca como predeterminada de compra o de venta, quita esa marca a las demás presentaciones del producto. Ficha técnica: [Commercial Relationship 27](../servicios/commercial-relationship.md#27-post-companiescompany_idcompany-product-presentations); guía principal: [Productos y precios, API 11](../principales/productos-y-precios.md#11-adoptar-una-presentación-en-la-empresa).

| | |
|---|---|
| Método y ruta | `POST /api/v1/companies/{company_id}/company-product-presentations` |
| URL completa | `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-product-presentations` |
| Permiso | `perm:commercial-relationship:company_product_presentations:create` |
| Clasificación | `WRITE` |

Cuerpo (modelo `CompanyProductPresentationCreate`; no admite campos adicionales):

| Campo | Tipo | Obligatorio | Validación / valor por defecto |
|---|---|---|---|
| `company_product_id` | UUID | Sí | Producto empresarial `ACTIVE` de la misma empresa |
| `global_product_presentation_id` | UUID | Sí | Presentación global `ACTIVE` y elegible del mismo producto global; no adoptada antes para ese producto |
| `internal_code` | string \| null | No | máx. 80; único en la empresa |
| `sku` | string \| null | No | máx. 80; único en la empresa |
| `reference_code` | string \| null | No | máx. 100 |
| `is_purchasable` | boolean | No | `true` |
| `is_sellable` | boolean | No | `true` |
| `is_default_purchase` | boolean | No | `false`; exige `is_purchasable: true` |
| `is_default_sale` | boolean | No | `false`; exige `is_sellable: true` |

```json
{
  "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
  "global_product_presentation_id": "8a9b0c1d-2e3f-4a4b-9c5d-6e7f8a9b0c1d",
  "internal_code": "PRD-0001-CJ",
  "sku": "7702001023456",
  "is_default_purchase": true,
  "is_default_sale": true
}
```

La respuesta `201` devuelve la presentación empresarial con cabecera `Location: /api/v1/company-product-presentations/{id}`. **Campo exacto:** `id`, que es el `company_product_presentation_id`.

**Posibles errores al adoptar:**

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `401` | `{"detail": "Se requiere un token de acceso Bearer"}` | Token ausente, vencido o inválido | Renovar la sesión y reintentar; si falla, volver al login |
| `403` | `COMMERCIAL_RELATIONSHIP.FORBIDDEN` | Falta `perm:commercial-relationship:company_product_presentations:create` | Mostrar que faltan permisos y el `trace_id` |
| `403` | `COMMERCIAL_RELATIONSHIP.OPERATIONAL_ACCESS_DENIED` | Operational Context rechazó la comprobación de membresía (suele faltar `perm:operational-context:application_users:read`) | Revisar los permisos del usuario |
| `404` | `COMMERCIAL_RELATIONSHIP.NOT_FOUND` | Sin membresía `ACTIVE` en la empresa, o empresa inexistente | Volver a leer el contexto operativo |
| `409` | `COMMERCIAL_RELATIONSHIP.DUPLICATE_PRESENTATION_ADOPTION` | La presentación global ya está adoptada para ese producto (activa o inactiva) | Buscarla con `?global_product_presentation_id=` y `status=ALL` |
| `409` | `COMMERCIAL_RELATIONSHIP.DUPLICATE_SKU` | Ya existe una presentación con ese `sku` en la empresa | Pedir otro SKU |
| `409` | `COMMERCIAL_RELATIONSHIP.DUPLICATE_INTERNAL_CODE` | Ya existe una presentación con ese `internal_code` en la empresa | Pedir otro código |
| `422` | `COMMERCIAL_RELATIONSHIP.DEFAULT_FLAG_INVALID` | Predeterminada de compra no comprable o de venta no vendible | Corregir las banderas |
| `422` | `COMMERCIAL_RELATIONSHIP.COMPANY_PRODUCT_NOT_FOUND` / `COMPANY_PRODUCT_INACTIVE` | El producto empresarial no es de la empresa o está inactivo | Elegir otro producto |
| `422` | `COMMERCIAL_RELATIONSHIP.GLOBAL_PRESENTATION_NOT_FOUND` / `GLOBAL_PRESENTATION_INACTIVE` / `GLOBAL_PRESENTATION_NOT_ELIGIBLE` | La presentación global no existe, está inactiva o no es elegible para adopción | Elegir otra presentación global |
| `422` | `COMMERCIAL_RELATIONSHIP.GLOBAL_PRESENTATION_OF_OTHER_PRODUCT` | La presentación global no pertenece al producto global del producto empresarial | Listar las presentaciones del producto correcto |
| `422` | `COMMERCIAL_RELATIONSHIP.COMPANY_INACTIVE` | La empresa está `INACTIVE` | No se pueden adoptar presentaciones |
| `422` | `COMMERCIAL_RELATIONSHIP.VALIDATION_ERROR` | Campo obligatorio ausente, longitud fuera de rango, UUID inválido o campo desconocido | Corregir el formulario |
| `503` | `COMMERCIAL_RELATIONSHIP.DEPENDENCY_UNAVAILABLE` | Operational Context o Product Catalog no responden (`dependency` lo indica) | Reintentar más tarde; nada se guardó |


## Cómo usarlo después

- En [Administración empresarial](../principales/administracion-empresarial.md#17-consultar-el-historial-de-una-venta-una-compra-o-un-producto): `{entity_id}` de la ruta de la API 17 con `entity_type=CompanyProductPresentation`.
- `lines[].company_product_presentation_id` en `POST /companies/{company_id}/sales` y `POST /companies/{company_id}/purchases`, siempre junto con `lines[].company_product_id` del mismo producto.
- Precios: campo `company_product_presentation_id` del cuerpo de la [API 17 de Productos y precios](../principales/productos-y-precios.md#17-registrar-un-precio-de-venta) y filtro `?company_product_presentation_id=` de la [API 18](../principales/productos-y-precios.md#18-consultar-los-precios-vigentes).
- Políticas de ganancia: `company_product_presentation_ids` de la [API 21](../principales/productos-y-precios.md#21-crear-una-política-de-ganancia), la [API 23](../principales/productos-y-precios.md#23-asignar-presentaciones-a-una-política) y la [API 24](../principales/productos-y-precios.md#24-retirar-presentaciones-de-una-política).
- Cobertura antes de comprar: `company_product_presentation_ids` de la [API 26](../principales/productos-y-precios.md#26-verificar-la-cobertura-de-políticas); filtro `?company_product_presentation_id=` de la [API 27](../principales/productos-y-precios.md#27-consultar-las-actualizaciones-automáticas-de-precio).

## Errores frecuentes

| Respuesta | Causa probable |
|---|---|
| `409 PURCHASE.DUPLICATE_PRESENTATION_IN_PURCHASE` | La misma presentación ya está en otra línea de la compra |
| `409 …REFERENCES_NOT_ELIGIBLE` | La presentación no pertenece al producto indicado, está `INACTIVE` o no es vendible/comprable |
| `409 PURCHASE.PRICING_POLICY_NOT_CONFIGURED` al confirmar una compra | La presentación no tiene política de ganancia en una lista activa y vigente de la moneda |
| `422 COMMERCIAL_RELATIONSHIP.PRESENTATION_NOT_SELLABLE` | Se usó una presentación no vendible en un precio o una política |
