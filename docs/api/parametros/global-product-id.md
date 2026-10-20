# Parámetro `global_product_id`

[← Parámetros](README.md) · [← Índice](../index.md) · Servicio propietario: [Product Catalog](../servicios/product-catalog.md)

| Propiedad | Valor |
|---|---|
| Qué representa | Un **producto del catálogo global** de SIO, compartido por todas las empresas (nombre canónico, marca, unidad base, atributos, presentaciones globales). Una empresa lo **adopta** para obtener su [producto empresarial](company-product-id.md) |
| Nombre en las rutas y cuerpos | `global_product_id` en Commercial Relationship y Product Inventory Query; `product_id` en las rutas de Product Catalog (`/products/{product_id}`) |
| Tipo | UUID (texto) |
| Obligatorio | Sí al adoptar un producto en una empresa; opcional como filtro |
| Ejemplo (ficticio) | `f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72` |
| Quién lo genera | Product Catalog, al crear el producto global (`id` de la respuesta) |
| Alcance | Global: cualquier usuario con el permiso de lectura lo ve, sin membresía |

## Cómo obtenerlo

| | |
|---|---|
| Método y ruta | `GET /api/v1/products` |
| URL completa | `https://sio-product-catalog-dev.onrender.com/api/v1/products` |
| Parámetros de consulta | `status` (`ACTIVE` o `INACTIVE`), `search` (máx. 200), `category_id` (UUID) con `include_descendants` (boolean, `false`), `brand_id`, `manufacturer_organization_id`, `group_id` (UUID), `identifier` (máx. 120; código de barras u otro identificador), `attribute_filters` (repetible, formato `CODIGO:valor`), `page` (≥1), `page_size` (1–100, por defecto 20) |
| Permiso | `perm:product-catalog:products:read` |
| Clasificación | `READ` |

```bash
curl -sS 'https://sio-product-catalog-dev.onrender.com/api/v1/products?search=acetaminofen&status=ACTIVE&page_size=10' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Respuesta `200` (modelo `PaginatedResponse[ProductResponse]`; valores ilustrativos; los objetos `completeness`, `warnings` y `detail` se describen en la ficha del servicio):

```json
{
  "items": [
    {
      "id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
      "version": 3,
      "created_at": "2025-11-02T12:00:00Z",
      "updated_at": "2026-01-10T16:20:00Z",
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "status": "ACTIVE",
      "product_type": "GOOD",
      "canonical_name": "Acetaminofén 500 mg tableta",
      "description": null,
      "global_brand_id": "b1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e",
      "manufacturer_organization_id": null,
      "base_unit_id": "d1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e",
      "first_used_at": null,
      "first_use_source": null,
      "completeness": {},
      "eligible_for_adoption": true,
      "warnings": [],
      "detail": null
    }
  ],
  "page": 1,
  "page_size": 10,
  "total_records": 1,
  "total_pages": 1
}
```

**Campo exacto:** `items[].id`. Solo adopta productos con `eligible_for_adoption: true`. El valor de `product_type` mostrado es ilustrativo; los valores permitidos están en la ficha de Product Catalog.

Otras formas de localizarlo, documentadas en la ficha del servicio: `GET /api/v1/products/by-identifier/{value}` (por código de barras u otro identificador) y `POST /api/v1/products/batch-lookup` (varios UUID a la vez).

## Si el producto global no existe todavía

Crear un producto global (`POST /api/v1/products`, permiso `perm:product-catalog:products:create`) es una operación `WRITE` de catálogo compartido que normalmente realizan administradores o supervisores, no el flujo de venta. El `global_product_id` es el campo `id` de la respuesta `201`. Ver la ficha de [Product Catalog](../servicios/product-catalog.md).

## Cómo usarlo después

- Adoptar en la empresa: `POST /companies/{company_id}/company-products` → campo `global_product_id` ([company_product_id](company-product-id.md)).
- Listar sus presentaciones globales: `GET /api/v1/products/{product_id}/presentations` ([company_product_presentation_id](company-product-presentation-id.md)).
- Filtro `?global_product_id=` al listar productos empresariales.

## Errores frecuentes

| Respuesta | Causa probable |
|---|---|
| `404 PRODUCT_CATALOG.NOT_FOUND` | El UUID no existe en el catálogo global |
| `422` al adoptar | El producto no es elegible (`eligible_for_adoption: false`) o está `INACTIVE` |
