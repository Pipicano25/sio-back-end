# Presentaciones

Una presentación describe **cómo existe físicamente** el producto: una unidad, un blíster de 10, una
caja de 100, un frasco de 120 ml. Es lo que las empresas adoptan para comprar y vender. Un producto
necesita al menos una presentación activa para estar completo.

Campos clave:

- `base_quantity`: cuántas unidades base equivale una presentación. Si la unidad base es `UND`, una
  caja de 100 tabletas tiene `base_quantity = 100`.
- `packaging_type_id`: el tipo de empaque (`BOX`, `TUBE`…).
- `content_quantity` + `content_unit_id`: el contenido declarado (15 `G`, 100 `ML`). Van juntos.
- `is_base`: marca la presentación base; como máximo una activa y siempre con `base_quantity = 1`.

Recurso de permiso: `products`.

| Ruta | Permiso |
| --- | --- |
| `GET /api/v1/products/{id}/presentations` (filtro `status`) | `read` |
| `GET /api/v1/presentations/{presentation_id}` | `read` |
| `POST /api/v1/products/{id}/presentations` | `update` |
| `PUT /api/v1/presentations/{presentation_id}` | `update` |
| `POST /api/v1/presentations/{presentation_id}/deactivate` · `/reactivate` | `deactivate` |
| `POST /api/v1/presentations/batch-lookup` | `read` |

---

## POST `/api/v1/products/{id}/presentations` — Crear

| Campo | Obligatorio | Regla |
| --- | --- | --- |
| `code` | Sí | Máx. 60; único dentro del producto, **incluidas las inactivas** |
| `name` | Sí | Máx. 160 |
| `packaging_type_id` | No | Tipo de empaque activo |
| `base_quantity` | No (`1`) | Mayor que 0; hasta 10 dígitos enteros y 8 decimales |
| `content_quantity` | No | Mayor que 0; exige `content_unit_id` |
| `content_unit_id` | No | Unidad activa; exige `content_quantity` |
| `display_order` | No (`0`) | ≥ 0 |
| `is_base` | No (`false`) | Si es `true`, `base_quantity` debe ser 1 |

```http
POST /api/v1/products/<id>/presentations
{
  "code": "TUBO_X_15G",
  "name": "Tubo x 15 g",
  "packaging_type_id": "<id TUBE>",
  "base_quantity": 1,
  "content_quantity": 15,
  "content_unit_id": "<id G>",
  "is_base": true
}
```

```json
{
  "id": "pr1…",
  "global_product_id": "<id>",
  "code": "TUBO_X_15G",
  "name": "Tubo x 15 g",
  "packaging_type_id": "<id TUBE>",
  "base_quantity": "1.00000000",
  "content_quantity": "15.0000",
  "content_unit_id": "<id G>",
  "display_order": 0,
  "is_base": true,
  "first_used_at": null,
  "first_use_source": null,
  "eligible_for_adoption": true,
  "status": "ACTIVE",
  "version": 1,
  "…": "…"
}
```

`eligible_for_adoption` es `true` si la presentación está activa y su producto es elegible.

| Error | Cuándo |
| --- | --- |
| `409 DUPLICATE_CODE` | El producto ya tiene ese código (aunque la otra esté inactiva) |
| `409 BASE_PRESENTATION_EXISTS` | Ya hay otra presentación base activa |
| `422 BASE_QUANTITY_MUST_BE_ONE` | `is_base: true` con `base_quantity` distinto de 1 |
| `422 VALIDATION_ERROR` | Contenido sin unidad (o al revés), cantidades ≤ 0 o con demasiados dígitos |
| `422 REFERENCE_INACTIVE` | Empaque o unidad de contenido inactivos |

## PUT `/api/v1/presentations/{presentation_id}` — Modificar

```json
{
  "name": "Tubo x 15 g",
  "display_order": 1,
  "packaging_type_id": "<id TUBE>",
  "base_quantity": 1,
  "content_quantity": 15,
  "content_unit_id": "<id G>",
  "is_base": true,
  "version": 1
}
```

Los campos **materiales** (`packaging_type_id`, `base_quantity`, `content_quantity`,
`content_unit_id`) definen qué es físicamente la presentación:

| Situación | Resultado |
| --- | --- |
| Sin marca de primer uso | Se pueden corregir |
| Con marca de primer uso | `422 PRESENTATION_LOCKED_BY_FIRST_USE`: cree una presentación nueva e inactive la anterior |

`name`, `display_order` e `is_base` se pueden cambiar siempre. `code` no se modifica.

## POST `…/deactivate` · `/reactivate`

Cuerpo `{ "version": n }`.

- Al inactivar se pierde la marca de base (`is_base`), y reactivar no la restaura.
- Si era la última presentación activa, el producto queda incompleto (`NO_ACTIVE_PRESENTATION`).
- Los códigos de barras de una presentación inactiva dejan de ser vigentes (`is_current: false`).

## POST `/api/v1/presentations/batch-lookup` — Hasta 100 presentaciones

```http
POST /api/v1/presentations/batch-lookup
{ "ids": ["pr1…", "pr9…"] }
```

```json
{
  "items": [
    { "id": "pr1…", "found": true, "global_product_id": "<id>", "status": "ACTIVE", "eligible_for_adoption": true, "base_quantity": "1.00000000", "first_used_at": null },
    { "id": "pr9…", "found": false, "global_product_id": null, "status": null, "eligible_for_adoption": null, "base_quantity": null, "first_used_at": null }
  ]
}
```
