# Paso 2. Otra búsqueda con el cursor anterior

Ejercicio 2: Cambio de filtros y cursor.

## Llamada

`GET /api/v1/companies/d22a0000-0000-4000-8000-000000000001/product-overviews?search=Abrilar&page_size=2&cursor=<CURSOR>`

Ejecuta: `ventas.test`.

### Por qué

- La huella de los filtros cambió: primera página de «Abrilar» con `pagination_reset = true` y `FILTERS_CHANGED`.

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
      "company_product_id": "d22e0000-0000-4000-8000-000000000005",
      "global_product_id": "d22f0000-0000-4000-8000-000000000005",
      "display_name": "Jarabe Abrilar 100 ml",
      "canonical_name": "ABRILAR JARABE 100ML",
      "internal_code": "P-0005",
      "reference_code": null,
      "status": "ACTIVE",
      "global_status": "ACTIVE",
      "product_type": "GOOD",
      "brand": null,
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
          "value": "7700000000005",
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
      "image_url": "https://catalogo.ejemplo.test/api/v1/public/product-images?ref=EJEMPLO-05",
      "presentations": [
        {
          "company_product_presentation_id": "d2280000-0000-4000-8000-000000000051",
          "global_product_presentation_id": "d2270000-0000-4000-8000-000000000051",
          "code": "FR",
          "name": "Frasco",
          "sku": "SKU-051",
          "internal_code": null,
          "status": "ACTIVE",
          "is_sellable": true,
          "base_quantity_factor": "1.0000",
          "price": {
            "price_list_id": "d22c0000-0000-4000-8000-000000000003",
            "price_list_item_id": "d2290000-0000-4000-8000-000000000051",
            "unit_price": "28000.00",
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
            "company_product_presentation_id": "d2280000-0000-4000-8000-000000000051",
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
  "pagination_reset": true,
  "pagination_reset_reason": "FILTERS_CHANGED",
  "partial": false,
  "partial_reason": null,
  "sort_applied": "display_name:asc",
  "resolved_at": "<asignado por el servicio>"
}
```
