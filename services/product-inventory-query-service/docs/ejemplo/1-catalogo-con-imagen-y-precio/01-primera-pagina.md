# Paso 1. Primera página con imagen

Ejercicio 1: Catálogo con imagen y precio.

## Llamada

`GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/product-overviews?search=Colgate&has_image=true&page_size=2`

Ejecuta: `ventas.test`.

### Por qué

- `search` lo evalúa Commercial Relationship y `has_image` Product Catalog, antes de elegir la página.
- De los 4 «Colgate», 3 tienen imagen: la primera página trae 2, en orden `display_name:asc`, y `has_next = true`.
- La imagen es de cada presentación (spec 024): `presentations[].has_image`, `asset_id` e `image_url`. `has_image=true` como filtro significa «al menos una presentación con imagen principal»: una presentación sin imagen propia trae `has_image = false` aunque otra presentación del producto tenga imagen (la «Caja x 12» del paso 2).
- `image_url` es la URL directa que construye Product Catalog: se usa sin token en `<img src>`.
- Sin `include_images`, las presentaciones no traen `images`.
- `ventas.test` ve precios y existencias, pero no los mínimos.

## Permiso

La URL exige `perm:product-inventory-query:product_overviews:read`.

Además, el usuario debe ser miembro `ACTIVE` de la empresa (lo verifica Operational Context con su token antes de cualquier otra consulta). No se exige asignación a la sucursal.

| Usuario | ¿Puede? | Respuesta | Motivo |
| --- | --- | --- | --- |
| `admin.test` | Sí | `200` | tiene `perm:all:all:all` |
| `supervisor.test` | Sí | `200` | tiene `perm:all:all:read` |
| `compras.test` | No | `403` | no tiene `perm:product-inventory-query:product_overviews:read` |
| `ventas.test` | Sí | `200` | tiene `perm:product-inventory-query:product_overviews:read` |
| `inventario.test` | Sí | `200` | tiene `perm:product-inventory-query:product_overviews:read` |
| `reportes.test` | No | `403` | no tiene `perm:product-inventory-query:product_overviews:read` |
| `consulta.test` | No | `403` | no tiene `perm:product-inventory-query:product_overviews:read` |

Respuesta sin permiso (`403`), que no revela el permiso exigido:

```json
{
  "type": "https://sio/errors/product-inventory-query/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/companies/d22a0000-0000-4000-8000-000000000001/product-overviews",
  "code": "PRODUCT_INVENTORY_QUERY.FORBIDDEN",
  "trace_id": "<asignado por el servicio>"
}
```

## Respuesta esperada

Estado `200`.

```json
{
  "items": [
    {
      "company_product_id": "d22e0000-0000-4000-8000-000000000002",
      "global_product_id": "d22f0000-0000-4000-8000-000000000002",
      "display_name": "Crema dental Colgate Herbal 75 ml",
      "canonical_name": "COLGATE HERBAL 75ML",
      "internal_code": "P-0002",
      "reference_code": null,
      "status": "ACTIVE",
      "global_status": "ACTIVE",
      "product_type": "GOOD",
      "brand": {
        "id": "d22c0000-0000-4000-8000-000000000001",
        "code": "COLGATE",
        "name": "Colgate (ficticia)"
      },
      "categories": [
        {
          "id": "d22c0000-0000-4000-8000-000000000002",
          "code": "CUIDADO",
          "name": "Cuidado personal (ficticia)",
          "is_primary": true
        }
      ],
      "identifiers": [
        {
          "type": "GTIN",
          "value": "7700000000002",
          "is_primary": true,
          "global_product_presentation_id": null
        }
      ],
      "base_unit": {
        "id": "d22d0000-0000-4000-8000-000000000001",
        "code": "UND",
        "name": "Unidad"
      },
      "presentations": [
        {
          "company_product_presentation_id": "d2280000-0000-4000-8000-000000000021",
          "global_product_presentation_id": "d2270000-0000-4000-8000-000000000021",
          "code": "UND",
          "name": "Unidad",
          "sku": "SKU-021",
          "internal_code": null,
          "status": "ACTIVE",
          "is_sellable": true,
          "base_quantity_factor": "1.0000",
          "has_image": true,
          "asset_id": "d2260000-0000-4000-8000-000000000021",
          "image_url": "https://catalogo.ejemplo.test/api/v1/public/product-images?ref=EJEMPLO-02",
          "price": {
            "price_list_id": "d22c0000-0000-4000-8000-000000000003",
            "price_list_item_id": "d2290000-0000-4000-8000-000000000021",
            "unit_price": "3900.00",
            "currency_code": "COP",
            "resolution": "PRICE_LIST_ITEM"
          }
        }
      ],
      "stock": {
        "base_unit": {
          "id": "d22d0000-0000-4000-8000-000000000001",
          "code": "UND",
          "name": "Unidad"
        },
        "total_base_quantity": "0.0000",
        "branches": [
          {
            "branch_id": "d22b0000-0000-4000-8000-000000000001",
            "base_quantity": "0.0000",
            "balance_state": "NOT_REGISTERED"
          },
          {
            "branch_id": "d22b0000-0000-4000-8000-000000000002",
            "base_quantity": "0.0000",
            "balance_state": "NOT_REGISTERED"
          },
          {
            "branch_id": "d22b0000-0000-4000-8000-000000000003",
            "base_quantity": "0.0000",
            "balance_state": "NOT_REGISTERED"
          }
        ],
        "equivalences": [
          {
            "company_product_presentation_id": "d2280000-0000-4000-8000-000000000021",
            "whole_units": 0,
            "remainder_base_quantity": "0.0000"
          }
        ]
      }
    },
    {
      "company_product_id": "d22e0000-0000-4000-8000-000000000003",
      "global_product_id": "d22f0000-0000-4000-8000-000000000003",
      "display_name": "Crema dental Colgate Kids 50 ml",
      "canonical_name": "COLGATE KIDS 50ML",
      "internal_code": "P-0003",
      "reference_code": null,
      "status": "ACTIVE",
      "global_status": "ACTIVE",
      "product_type": "GOOD",
      "brand": {
        "id": "d22c0000-0000-4000-8000-000000000001",
        "code": "COLGATE",
        "name": "Colgate (ficticia)"
      },
      "categories": [
        {
          "id": "d22c0000-0000-4000-8000-000000000002",
          "code": "CUIDADO",
          "name": "Cuidado personal (ficticia)",
          "is_primary": true
        }
      ],
      "identifiers": [
        {
          "type": "GTIN",
          "value": "7700000000003",
          "is_primary": true,
          "global_product_presentation_id": null
        }
      ],
      "base_unit": {
        "id": "d22d0000-0000-4000-8000-000000000001",
        "code": "UND",
        "name": "Unidad"
      },
      "presentations": [
        {
          "company_product_presentation_id": "d2280000-0000-4000-8000-000000000031",
          "global_product_presentation_id": "d2270000-0000-4000-8000-000000000031",
          "code": "UND",
          "name": "Unidad",
          "sku": "SKU-031",
          "internal_code": null,
          "status": "ACTIVE",
          "is_sellable": true,
          "base_quantity_factor": "1.0000",
          "has_image": true,
          "asset_id": "d2260000-0000-4000-8000-000000000031",
          "image_url": "https://catalogo.ejemplo.test/api/v1/public/product-images?ref=EJEMPLO-03",
          "price": {
            "price_list_id": "d22c0000-0000-4000-8000-000000000003",
            "price_list_item_id": "d2290000-0000-4000-8000-000000000031",
            "unit_price": "3200.00",
            "currency_code": "COP",
            "resolution": "PRICE_LIST_ITEM"
          }
        }
      ],
      "stock": {
        "base_unit": {
          "id": "d22d0000-0000-4000-8000-000000000001",
          "code": "UND",
          "name": "Unidad"
        },
        "total_base_quantity": "0.0000",
        "branches": [
          {
            "branch_id": "d22b0000-0000-4000-8000-000000000001",
            "base_quantity": "0.0000",
            "balance_state": "NOT_REGISTERED"
          },
          {
            "branch_id": "d22b0000-0000-4000-8000-000000000002",
            "base_quantity": "0.0000",
            "balance_state": "NOT_REGISTERED"
          },
          {
            "branch_id": "d22b0000-0000-4000-8000-000000000003",
            "base_quantity": "0.0000",
            "balance_state": "NOT_REGISTERED"
          }
        ],
        "equivalences": [
          {
            "company_product_presentation_id": "d2280000-0000-4000-8000-000000000031",
            "whole_units": 0,
            "remainder_base_quantity": "0.0000"
          }
        ]
      }
    }
  ],
  "page_size": 2,
  "has_next": true,
  "next_cursor": "<CURSOR>",
  "pagination_reset": false,
  "pagination_reset_reason": null,
  "partial": false,
  "partial_reason": null,
  "sort_applied": "display_name:asc",
  "resolved_at": "<asignado por el servicio>"
}
```

## Variables que se guardan

- `<CURSOR>` = `next_cursor` de la respuesta.
