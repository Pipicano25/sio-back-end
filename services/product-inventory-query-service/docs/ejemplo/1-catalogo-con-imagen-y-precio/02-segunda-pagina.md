# Paso 2. Página siguiente con el cursor

Ejercicio 1: Catálogo con imagen y precio.

## Llamada

`GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/product-overviews?search=Colgate&has_image=true&page_size=2&cursor=<CURSOR>`

Ejecuta: `ventas.test`.

### Por qué

- El cursor continúa después del último producto entregado: ninguno se repite.
- La «Caja x 12» no tiene precio en la lista: `unit_price = null` con `resolution = NO_PRICE_IN_LIST`; nunca se usa el precio de otra lista ni se inventa.
- Es la última página: `has_next = false` y `next_cursor = null`.

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
      "company_product_id": "d22e0000-0000-4000-8000-000000000001",
      "global_product_id": "d22f0000-0000-4000-8000-000000000001",
      "display_name": "Crema dental Colgate Triple Acción 100 ml",
      "canonical_name": "COLGATE TRIPLE ACCION 100ML",
      "internal_code": "P-0001",
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
          "value": "7700000000001",
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
          "company_product_presentation_id": "d2280000-0000-4000-8000-000000000011",
          "global_product_presentation_id": "d2270000-0000-4000-8000-000000000011",
          "code": "UND",
          "name": "Unidad",
          "sku": "SKU-011",
          "internal_code": null,
          "status": "ACTIVE",
          "is_sellable": true,
          "base_quantity_factor": "1.0000",
          "has_image": true,
          "asset_id": "d2260000-0000-4000-8000-000000000011",
          "image_url": "https://catalogo.ejemplo.test/api/v1/public/product-images?ref=EJEMPLO-01",
          "price": {
            "price_list_id": "d22c0000-0000-4000-8000-000000000003",
            "price_list_item_id": "d2290000-0000-4000-8000-000000000011",
            "unit_price": "4500.00",
            "currency_code": "COP",
            "resolution": "PRICE_LIST_ITEM"
          }
        },
        {
          "company_product_presentation_id": "d2280000-0000-4000-8000-000000000012",
          "global_product_presentation_id": "d2270000-0000-4000-8000-000000000012",
          "code": "CJ12",
          "name": "Caja x 12",
          "sku": "SKU-012",
          "internal_code": null,
          "status": "ACTIVE",
          "is_sellable": true,
          "base_quantity_factor": "12.0000",
          "has_image": false,
          "asset_id": null,
          "image_url": null,
          "price": {
            "price_list_id": null,
            "price_list_item_id": null,
            "unit_price": null,
            "currency_code": null,
            "resolution": "NO_PRICE_IN_LIST"
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
            "company_product_presentation_id": "d2280000-0000-4000-8000-000000000011",
            "whole_units": 0,
            "remainder_base_quantity": "0.0000"
          },
          {
            "company_product_presentation_id": "d2280000-0000-4000-8000-000000000012",
            "whole_units": 0,
            "remainder_base_quantity": "0.0000"
          }
        ]
      }
    }
  ],
  "page_size": 2,
  "has_next": false,
  "next_cursor": null,
  "pagination_reset": false,
  "pagination_reset_reason": null,
  "partial": false,
  "partial_reason": null,
  "sort_applied": "display_name:asc",
  "resolved_at": "<asignado por el servicio>"
}
```
