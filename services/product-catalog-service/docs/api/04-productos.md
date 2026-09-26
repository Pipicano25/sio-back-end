# Productos

El producto global es la identidad común de un artículo: qué es, de qué marca, quién lo fabrica y
en qué unidad se controla. Sus categorías, valores, presentaciones, códigos, grupos y activos cuelgan
de él y se documentan en sus propios archivos.

Recurso de permiso: `products`.

| Ruta | Permiso | Uso |
| --- | --- | --- |
| `GET /api/v1/products` | `read` | Buscar (paginada) |
| `GET /api/v1/products/{id}` | `read` | Consultar (con `?expand=detail` trae todo) |
| `GET /api/v1/products/{id}/completeness` | `read` | Solo el indicador de completitud |
| `GET /api/v1/products/{id}/applicable-attributes` | `read` | Atributos que aplican al producto |
| `GET /api/v1/products/by-identifier/{value}` | `read` | Buscar por código escaneado |
| `POST /api/v1/products/batch-lookup` | `read` | Consultar hasta 100 productos |
| `POST /api/v1/products` | `create` | Crear |
| `PUT /api/v1/products/{id}` | `update` | Modificar |
| `POST /api/v1/products/{id}/deactivate` · `/reactivate` | `deactivate` | Inactivar / reactivar |

---

## Representación de un producto

Todas las rutas que devuelven un producto usan esta forma:

```json
{
  "id": "p1…",
  "product_type": "GOOD",
  "canonical_name": "Acetaminofén 500 mg tableta",
  "description": null,
  "global_brand_id": "<id MK>",
  "manufacturer_organization_id": "<id Tecnoquímicas en Party Identity>",
  "base_unit_id": "<id UND>",
  "first_used_at": null,
  "first_use_source": null,
  "completeness": {
    "is_complete": false,
    "issues": ["NO_ACTIVE_PRESENTATION"],
    "missing_attribute_definition_ids": [],
    "out_of_classification_value_ids": []
  },
  "eligible_for_adoption": false,
  "warnings": [],
  "detail": null,
  "status": "ACTIVE",
  "version": 1,
  "created_at": "…", "updated_at": "…", "created_by": "…", "updated_by": "…"
}
```

- `completeness` y `eligible_for_adoption` se **calculan en cada consulta**; nunca se guardan (ver
  `api-guide.md` §4).
- `warnings` solo trae contenido en las respuestas de alta o modificación.
- `detail` solo se llena con `?expand=detail`.

---

## POST `/api/v1/products` — Crear

| Campo | Obligatorio | Regla |
| --- | --- | --- |
| `product_type` | Sí | Por ahora solo `GOOD` |
| `canonical_name` | Sí | Máx. 200; espacios repetidos se reducen |
| `description` | No | |
| `global_brand_id` | No | Marca activa |
| `manufacturer_organization_id` | No | Organización que existe en Party Identity |
| `base_unit_id` | Sí | Unidad de medida activa |

```http
POST /api/v1/products
{
  "product_type": "GOOD",
  "canonical_name": "Acetaminofén 500 mg tableta",
  "global_brand_id": "<id MK>",
  "manufacturer_organization_id": "<id Tecnoquímicas>",
  "base_unit_id": "<id UND>"
}
```

Respuesta `201` con el producto y `Location: /api/v1/products/{id}`. Nace `ACTIVE` pero normalmente
**incompleto**: le faltan categoría y presentación.

**Fabricante.** Si se envía, el servicio consulta Party Identity con el token del usuario:

| Resultado en Party Identity | Respuesta |
| --- | --- |
| Existe | Se acepta |
| No existe | `422 MANUFACTURER_NOT_FOUND` |
| El usuario no tiene permiso allí | `403 MANUFACTURER_ACCESS_DENIED` |
| No responde a tiempo o falla | `503 DEPENDENCY_UNAVAILABLE` (reintentar) |

**Posible duplicado.** Si otro producto tiene el mismo nombre normalizado (sin mayúsculas, tildes ni
espacios repetidos) y la misma marca (o ambos sin marca), el alta se hace igual y la respuesta
incluye:

```json
"warnings": [
  { "code": "POSSIBLE_DUPLICATE", "message": "…", "matching_product_ids": ["p0…"] }
]
```

Otros errores: `422 REFERENCE_INACTIVE` (marca o unidad inactivas), `422 REFERENCE_NOT_FOUND`.

## PUT `/api/v1/products/{id}` — Modificar

```json
{
  "canonical_name": "Acetaminofén 500 mg tableta recubierta",
  "description": null,
  "global_brand_id": "<id MK>",
  "manufacturer_organization_id": "<id Tecnoquímicas>",
  "base_unit_id": "<id UND>",
  "version": 1
}
```

- `PUT` reemplaza: si no se envía `global_brand_id` o `manufacturer_organization_id`, se quitan.
- Party Identity **solo se consulta si el fabricante cambia** a otro valor. Reenviar el mismo,
  quitarlo o editar otros campos funciona aunque Party Identity esté caído.
- `base_unit_id` se puede corregir solo mientras el producto no tenga **marca de primer uso**; con
  marca → `422 BASE_UNIT_LOCKED_BY_FIRST_USE`.
- `product_type` y los campos de primer uso no se pueden enviar → `422 IMMUTABLE_FIELD`.
- Solo se recalcula la advertencia de duplicado si cambian el nombre o la marca.

## GET `/api/v1/products` — Buscar (paginada)

| Parámetro | Descripción |
| --- | --- |
| `search` | Parte del nombre, sin mayúsculas ni tildes (`cafe` encuentra "Café") |
| `status` | `ACTIVE` / `INACTIVE` |
| `category_id` | Productos con esa categoría asignada |
| `include_descendants=true` | Con `category_id`, incluye subcategorías |
| `brand_id` | Por marca |
| `manufacturer_organization_id` | Por fabricante |
| `group_id` | Con ese grupo asignado y activo |
| `identifier` | Por código: familia GTIN (cualquier variante de ceros), `BARCODE` u `OTHER` |
| `attribute_filters` | `CODIGO:valor`, repetible; solo atributos filtrables |

```http
GET /api/v1/products?search=acetaminofen&category_id=<id MEDICAMENTOS>&include_descendants=true
GET /api/v1/products?attribute_filters=CONCENTRACION_MG:500
GET /api/v1/products?identifier=7702057781194
```

- `attribute_filters` convierte el valor según el tipo del atributo: número, `true`/`false`, fecha
  `AAAA-MM-DD` o el **código** de la opción (`TALLA_PANAL:L`).
- Un atributo no filtrable en ninguna categoría → `422 ATTRIBUTE_NOT_FILTERABLE`; un valor que no
  corresponde al tipo → `422 VALIDATION_ERROR`.
- Los parámetros desconocidos se ignoran.

## GET `/api/v1/products/{id}` — Consultar

```http
GET /api/v1/products/<id>?expand=detail
```

Con `expand=detail`, `detail` trae los elementos **vigentes**:

```json
"detail": {
  "categories": [ { "global_category_id": "…", "is_primary": true, "…": "…" } ],
  "presentations": [ { "code": "CAJA_X_100", "base_quantity": "100.00000000", "eligible_for_adoption": true, "…": "…" } ],
  "identifiers": [ { "identifier_type": "EAN", "value": "7702057781194", "…": "…" } ],
  "attribute_values": [ { "attribute_definition_id": "…", "decimal_value": "500.00000000", "out_of_classification": false, "…": "…" } ],
  "group_assignments": [],
  "assets": []
}
```

## GET `/api/v1/products/{id}/completeness`

Solo el indicador:

```json
{
  "is_complete": false,
  "issues": ["MISSING_REQUIRED_ATTRIBUTE"],
  "missing_attribute_definition_ids": ["<id CONCENTRACION_MG>"],
  "out_of_classification_value_ids": []
}
```

Problemas posibles: `MISSING_MINIMUM_DATA`, `BASE_UNIT_NOT_FOUND`, `NO_ACTIVE_CATEGORY`,
`NO_PRIMARY_CATEGORY`, `MISSING_REQUIRED_ATTRIBUTE`, `INCONSISTENT_REQUIRED_VALUE`,
`NO_ACTIVE_PRESENTATION`.

## GET `/api/v1/products/{id}/applicable-attributes`

Qué atributos admite el producto según las categorías que tiene asignadas (sin herencia):

```json
[
  {
    "attribute_definition_id": "<id CONCENTRACION_MG>",
    "code": "CONCENTRACION_MG",
    "name": "Concentración",
    "data_type": "DECIMAL",
    "unit_of_measure_id": "<id MG>",
    "is_required": true,
    "is_filterable": true,
    "display_order": 1,
    "category_ids": ["<id ANALGESICOS>"]
  }
]
```

Si varias categorías usan el mismo atributo, se une: es obligatorio si alguna lo exige.

## GET `/api/v1/products/by-identifier/{value}` — Código escaneado

```http
GET /api/v1/products/by-identifier/7702057781194
```

```json
{
  "product": { "id": "p1…", "canonical_name": "Acetaminofén 500 mg tableta", "…": "…" },
  "presentation": { "id": "pr1…", "code": "CAJA_X_100", "…": "…" },
  "identifier": { "identifier_type": "EAN", "value": "7702057781194", "canonical_value": "07702057781194", "…": "…" },
  "is_current": true
}
```

- El valor se normaliza (sin espacios ni guiones) y para la familia GTIN se compara en 14 dígitos.
- Resuelve la familia GTIN y `BARCODE`, que son únicos en todo el catálogo. **No resuelve `OTHER`**
  (use el filtro `identifier` de la búsqueda).
- `is_current` es `true` solo si identificador, producto y presentación están activos.
- `404` si ningún producto tiene ese código.

## POST `/api/v1/products/batch-lookup` — Hasta 100 productos

Para servicios que validan antes de adoptar.

```http
POST /api/v1/products/batch-lookup
{ "ids": ["p1…", "p2…"] }
```

```json
{
  "items": [
    { "id": "p1…", "found": true, "status": "ACTIVE", "is_complete": true, "eligible_for_adoption": true, "first_used_at": null },
    { "id": "p2…", "found": false, "status": null, "is_complete": null, "eligible_for_adoption": null, "first_used_at": null }
  ]
}
```

Vacío → `422`; más de 100 → `422 BATCH_LIMIT_EXCEEDED`; los repetidos se ignoran.

## POST `/api/v1/products/{id}/deactivate` · `/reactivate`

Cuerpo `{ "version": n }`. Permiso `products:deactivate`.

- Inactivar **no se propaga**: categorías, presentaciones, códigos, grupos y activos se conservan.
- Un producto inactivo no se puede adoptar, y sobre sus elementos solo se permite consultar e
  inactivar (crear o modificar → `422 PRODUCT_INACTIVE`).
- Reactivar no exige que la marca o la unidad base sigan activas.
