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

| | |
|---|---|
| Método y ruta | `GET /api/v1/products/{product_id}/presentations` |
| URL completa | `https://sio-product-catalog-dev.onrender.com/api/v1/products/{product_id}/presentations` |
| Parámetros de ruta | `product_id` (UUID del producto global) — [cómo obtenerlo](global-product-id.md) |
| Parámetros de consulta | `status` (`ACTIVE` o `INACTIVE`; sin filtro devuelve todas) |
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
    "id": "cb3f20d2-d67f-4944-8a4d-97bc9aa54f94",
    "version": 1,
    "created_at": "2026-10-19T15:04:05Z",
    "updated_at": "2026-10-19T15:04:05Z",
    "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
    "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
    "status": "ACTIVE",
    "global_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
    "code": "CJ100",
    "name": "Caja x 100",
    "packaging_type_id": "e2f3a4b5-c6d7-4e8f-9a0b-1c2d3e4f5a6b",
    "base_quantity": "100",
    "content_quantity": null,
    "content_unit_id": null,
    "display_order": 1,
    "is_base": false,
    "first_used_at": "2026-10-19T15:04:05Z",
    "first_use_source": "MANUAL",
    "eligible_for_adoption": true
  }
]
```

**Campo exacto:** `[].id`. `is_base` marca la presentación base (una por producto), `base_quantity` cuántas unidades base contiene y `code` su código legible.

Si ya se conoce la presentación empresarial, `GET https://sio-commercial-relationship-dev.onrender.com/api/v1/company-product-presentations/{company_product_presentation_id}` devuelve el campo `global_product_presentation_id` de origen.

## Si la presentación no existe todavía (operación `WRITE`)

| | |
|---|---|
| Método y ruta | `POST /api/v1/products/{product_id}/presentations` |
| URL completa | `https://sio-product-catalog-dev.onrender.com/api/v1/products/{product_id}/presentations` |
| Permiso | `perm:product-catalog:products:update` |
| Clasificación | `WRITE` |

Cuerpo (`PresentationCreate`): `code` (único por producto), `name`, `packaging_type_id` opcional, `base_quantity` (por defecto `1`), `content_quantity` y `content_unit_id` opcionales, `display_order`, `is_base`. Ver la [operación 68](../servicios/product-catalog.md#68-post-productsproduct_idpresentations) de Product Catalog.

```json
{
  "code": "CJ100",
  "name": "Caja x 100",
  "packaging_type_id": "e2f3a4b5-c6d7-4e8f-9a0b-1c2d3e4f5a6b",
  "base_quantity": "100",
  "display_order": 1,
  "is_base": false
}
```

La respuesta `201` devuelve `PresentationResponse`; el `global_product_presentation_id` es su campo `id`.

## Cómo usarlo después

- Adoptar la presentación en la empresa: `POST https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-product-presentations` con `company_product_id` y `global_product_presentation_id` ([company_product_presentation_id](company-product-presentation-id.md)). El producto global debe estar adoptado antes ([company_product_id](company-product-id.md)).
- Filtrar las presentaciones empresariales ya adoptadas: `GET …/companies/{company_id}/company-product-presentations?global_product_presentation_id=…`.
- Consultar sus códigos de barras e identificadores: `GET …/presentations/{presentation_id}/identifiers` de Product Catalog.

## Errores frecuentes

| Respuesta | Causa probable |
|---|---|
| `404 PRODUCT_CATALOG.NOT_FOUND` | El producto o la presentación no existe |
| `409` al adoptar | La presentación global ya fue adoptada para ese producto empresarial, o pertenece a otro producto global |
| `409 VERSION_CONFLICT` | El `version` enviado al actualizar no es el actual |
