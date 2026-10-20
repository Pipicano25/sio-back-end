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

| | |
|---|---|
| Método y ruta | `GET /api/v1/companies/{company_id}/company-product-presentations` |
| URL completa | `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-product-presentations` |
| Parámetros de ruta | `company_id` (UUID) — [cómo obtenerlo](company-id.md) |
| Parámetros de consulta | `company_product_id` (UUID; **úsalo para traer solo las presentaciones del producto elegido**), `global_product_presentation_id` (UUID), `search` (máx. 100), `status` (`ACTIVE`, `INACTIVE`, `ALL`), `is_purchasable`, `is_sellable` (boolean), `page`, `page_size` (1–100, por defecto 20) |
| Permiso | `perm:commercial-relationship:company_product_presentations:read` |
| Clasificación | `READ` |

```bash
curl -sS 'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/company-product-presentations?company_product_id=e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61&is_sellable=true' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
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
      "global_product_presentation_id": "c6c7d8e9-f0a1-4b2c-9d3e-4f5a6b7c8d94",
      "internal_code": "PRD-0001-U",
      "sku": "7701234567890",
      "reference_code": null,
      "is_purchasable": true,
      "is_sellable": true,
      "is_default_purchase": false,
      "is_default_sale": true
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

**Campo exacto:** `items[].id`. Preselecciona la que tenga `is_default_sale: true` (ventas) o `is_default_purchase: true` (compras). El nombre y la cantidad base de la presentación («caja × 100») no están en este objeto: provienen de la presentación global (`global_product_presentation_id`) en Product Catalog, o directamente de [Product Inventory Query](../servicios/product-inventory-query.md), que ya combina ambos.

## Si la presentación no está adoptada todavía (operación `WRITE`)

1. Lista las presentaciones globales del producto en Product Catalog:

| | |
|---|---|
| Método y ruta | `GET /api/v1/products/{product_id}/presentations` (`product_id` = [global_product_id](global-product-id.md)) |
| URL completa | `https://sio-product-catalog-dev.onrender.com/api/v1/products/{product_id}/presentations` |
| Parámetros de consulta | `status` (`ACTIVE` o `INACTIVE`) |
| Permiso | `perm:product-catalog:products:read` |
| Respuesta | `200` con un **array** (sin paginación) de `PresentationResponse`: `id`, `global_product_id`, `code`, `name`, `packaging_type_id`, `base_quantity`, `content_quantity`, `content_unit_id`, `display_order`, `is_base`, `status`, `eligible_for_adoption`, … |

El `global_product_presentation_id` es el campo `id` de cada elemento.

2. Adóptala en la empresa:

| | |
|---|---|
| Método y ruta | `POST /api/v1/companies/{company_id}/company-product-presentations` |
| URL completa | `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-product-presentations` |
| Permiso | `perm:commercial-relationship:company_product_presentations:create` |
| Clasificación | `WRITE` |

Cuerpo (modelo `CompanyProductPresentationCreate`; no admite campos adicionales):

| Campo | Tipo | Obligatorio | Validación / valor por defecto |
|---|---|---|---|
| `company_product_id` | UUID | Sí | Producto empresarial de la misma empresa |
| `global_product_presentation_id` | UUID | Sí | Presentación global del mismo producto global |
| `internal_code` | string \| null | No | máx. 80 |
| `sku` | string \| null | No | máx. 80 |
| `reference_code` | string \| null | No | máx. 100 |
| `is_purchasable` | boolean | No | `true` |
| `is_sellable` | boolean | No | `true` |
| `is_default_purchase` | boolean | No | `false` |
| `is_default_sale` | boolean | No | `false` |

```json
{
  "company_product_id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
  "global_product_presentation_id": "c6c7d8e9-f0a1-4b2c-9d3e-4f5a6b7c8d94",
  "sku": "7701234567890",
  "is_default_sale": true
}
```

La respuesta `201` devuelve la presentación empresarial; el identificador es su campo `id`.

## Cómo usarlo después

- `lines[].company_product_presentation_id` en `POST /companies/{company_id}/sales` y `POST /companies/{company_id}/purchases`, siempre junto con `lines[].company_product_id` del mismo producto.
- Precios por presentación en listas de precios (`price-list-items`) y políticas de ganancia.

## Errores frecuentes

| Respuesta | Causa probable |
|---|---|
| `409 PURCHASE.DUPLICATE_PRESENTATION_IN_PURCHASE` | La misma presentación ya está en otra línea de la compra |
| `409 …REFERENCES_NOT_ELIGIBLE` | La presentación no pertenece al producto indicado, está `INACTIVE` o no es vendible/comprable |
