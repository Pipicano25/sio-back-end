# Paso 4. Otro orden

Ejercicio 2: Cambio de filtros y cursor.

## Llamada

`GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/product-overviews?search=Colgate&page_size=2&sort=internal_code:desc&cursor=<CURSOR>`

Ejecuta: `ventas.test`.

### Por qué

- `SORT_CHANGED`: primera página en el orden pedido, informado en `sort_applied`.

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
      "company_product_id": "d22e0000-0000-4000-8000-000000000004",
      "global_product_id": "d22f0000-0000-4000-8000-000000000004",
      "display_name": "Crema dental Colgate Máxima 150 ml",
      "canonical_name": "COLGATE MAXIMA 150ML",
      "internal_code": "P-0004",
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
          "value": "7700000000004",
          "is_primary": true,
          "global_product_presentation_id": null
        }
      ],
      "base_unit": {
        "id": "d22d0000-0000-4000-8000-000000000001",
        "code": "UND",
        "name": "Unidad"
      },
      "has_image": false,
      "image_url": null,
      "presentations": [
        {
          "company_product_presentation_id": "d2280000-0000-4000-8000-000000000041",
          "global_product_presentation_id": "d2270000-0000-4000-8000-000000000041",
          "code": "UND",
          "name": "Unidad",
          "sku": "SKU-041",
          "internal_code": null,
          "status": "ACTIVE",
          "is_sellable": true,
          "base_quantity_factor": "1.0000",
          "price": {
            "price_list_id": "d22c0000-0000-4000-8000-000000000003",
            "price_list_item_id": "d2290000-0000-4000-8000-000000000041",
            "unit_price": "6100.00",
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
            "company_product_presentation_id": "d2280000-0000-4000-8000-000000000041",
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
      "has_image": true,
      "image_url": "https://catalogo.ejemplo.test/api/v1/public/product-images?ref=EJEMPLO-03",
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
  "next_cursor": "<asignado por el servicio>",
  "pagination_reset": true,
  "pagination_reset_reason": "SORT_CHANGED",
  "partial": false,
  "partial_reason": null,
  "sort_applied": "internal_code:desc",
  "resolved_at": "<asignado por el servicio>"
}
```
