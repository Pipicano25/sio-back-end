# Parámetro `company_product_id`

[← Parámetros](README.md) · [← Índice](../index.md) · Servicio propietario: [Commercial Relationship](../servicios/commercial-relationship.md)

| Propiedad | Valor |
|---|---|
| Qué representa | Un **producto adoptado por una empresa**: la versión empresarial (código interno, nombre comercial, moneda, control de inventario) de un producto del catálogo global. Ventas, compras y existencias trabajan con este identificador, no con el producto global |
| Nombre en las rutas y cuerpos | `company_product_id` |
| Tipo | UUID (texto) |
| Obligatorio | Sí en cada línea de venta y de compra, y en consultas de existencias por producto |
| Ejemplo (ficticio) | `e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61` |
| Quién lo genera | Commercial Relationship, al adoptar el producto global (`id` de la respuesta) |
| Alcance | Empresa |

## Cómo obtenerlo

| | |
|---|---|
| Método y ruta | `GET /api/v1/companies/{company_id}/company-products` |
| URL completa | `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-products` |
| Parámetros de ruta | `company_id` (UUID) — [cómo obtenerlo](company-id.md) |
| Parámetros de consulta | `page` (≥1), `page_size` (1–100, por defecto 20), `search` (máx. 100), `status` (`ACTIVE`, `INACTIVE`, `ALL`), `is_purchasable`, `is_sellable`, `inventory_control_enabled` (boolean), `global_product_id` (UUID) |
| Permiso | `perm:commercial-relationship:company_products:read` |
| Clasificación | `READ` |

```bash
curl -sS 'https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/550e8400-e29b-41d4-a716-446655440000/company-products?is_sellable=true&status=ACTIVE' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Respuesta `200` (modelo `PaginatedResponse[CompanyProductResponse]`; valores ilustrativos):

```json
{
  "items": [
    {
      "id": "e3f4a5b6-c7d8-4e9f-8a0b-1c2d3e4f5a61",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "ACTIVE",
      "version": 1,
      "created_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "updated_by": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
      "created_at": "2026-02-05T08:00:00Z",
      "updated_at": "2026-02-05T08:00:00Z",
      "global_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
      "internal_code": "PRD-0001",
      "reference_code": null,
      "display_name": "Acetaminofén 500 mg",
      "short_name": "Acetaminofén",
      "currency_code": "COP",
      "inventory_control_enabled": true,
      "lot_tracking_enabled": false,
      "expiration_tracking_enabled": true,
      "is_purchasable": true,
      "is_sellable": true,
      "purchase_tax_percentage": "19.00"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

**Campo exacto:** `items[].id`. Para vender, filtra `is_sellable=true`; para comprar, `is_purchasable=true`. `global_product_id` enlaza con el [producto del catálogo global](global-product-id.md).

**Alternativa para pantallas de consulta:** [Product Inventory Query](../servicios/product-inventory-query.md) devuelve en una sola llamada el producto empresarial con precios y existencias (`GET /companies/{company_id}/product-overviews`); allí el identificador aparece también como `company_product_id`.

## Si el producto no está adoptado todavía (operación `WRITE`)

1. Localiza el producto en el catálogo global: [global_product_id](global-product-id.md).
2. Adóptalo en la empresa:

| | |
|---|---|
| Método y ruta | `POST /api/v1/companies/{company_id}/company-products` |
| URL completa | `https://sio-commercial-relationship-dev.onrender.com/api/v1/companies/{company_id}/company-products` |
| Permiso | `perm:commercial-relationship:company_products:create` |
| Clasificación | `WRITE` |

Cuerpo (modelo `CompanyProductCreate`; no admite campos adicionales):

| Campo | Tipo | Obligatorio | Validación / valor por defecto |
|---|---|---|---|
| `global_product_id` | UUID | Sí | Debe existir en Product Catalog y ser elegible para adopción |
| `internal_code` | string | Sí | 1 a 60 caracteres; único por empresa |
| `reference_code` | string \| null | No | máx. 100 |
| `display_name` | string | Sí | 1 a 200 |
| `short_name` | string \| null | No | máx. 160 |
| `currency_code` | string | Sí | 1 a 10 caracteres (por ejemplo `COP`) |
| `inventory_control_enabled` | boolean | No | `true` |
| `lot_tracking_enabled` | boolean | No | `false` |
| `expiration_tracking_enabled` | boolean | No | `false` |
| `is_purchasable` | boolean | No | `true` |
| `is_sellable` | boolean | No | `true` |

```json
{
  "global_product_id": "f4a5b6c7-d8e9-4f0a-9b1c-2d3e4f5a6b72",
  "internal_code": "PRD-0001",
  "display_name": "Acetaminofén 500 mg",
  "short_name": "Acetaminofén",
  "currency_code": "COP",
  "inventory_control_enabled": true,
  "expiration_tracking_enabled": true
}
```

La respuesta `201` devuelve el producto empresarial; el `company_product_id` es su campo `id`. Después hay que adoptar al menos una [presentación empresarial](company-product-presentation-id.md), porque las líneas de venta y compra exigen ambas cosas.

## Cómo usarlo después

- Líneas de venta y compra: `lines[].company_product_id` junto con `lines[].company_product_presentation_id`.
- Existencias: filtro `?company_product_id=` en Inventory y ruta de políticas por producto.
- Precios: listas de precios y políticas de ganancia en Commercial Relationship.

## Errores frecuentes

| Respuesta | Causa probable |
|---|---|
| `404 COMMERCIAL_RELATIONSHIP.NOT_FOUND` | El producto no pertenece a la empresa o el usuario no tiene membresía |
| `409 SALES.REFERENCES_NOT_ELIGIBLE` / `PURCHASE.REFERENCES_NOT_ELIGIBLE` | Producto `INACTIVE`, no vendible o no comprable, o la presentación no pertenece a ese producto |
