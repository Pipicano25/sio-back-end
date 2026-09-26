# Clasificación del producto y valores de atributo

Dos operaciones que dan contenido al producto:

1. **Asignarle categorías**, de las que depende qué atributos aplican.
2. **Registrar los valores** de esos atributos.

Ambas exigen que el producto esté `ACTIVE`; sobre un producto inactivo solo se consulta e inactiva
(`422 PRODUCT_INACTIVE`).

---

## 1. Categorías del producto — `/api/v1/products/{id}/categories`

| Ruta | Permiso |
| --- | --- |
| `GET …/categories` (filtro `status`) | `products:read` |
| `POST …/categories` | `products:update` |
| `POST …/categories/{association_id}/set-primary` | `products:update` |
| `POST …/categories/{association_id}/deactivate` | `products:deactivate` |

### POST — Asignar una categoría

```http
POST /api/v1/products/<id>/categories
{ "global_category_id": "<id ANALGESICOS>" }
```

```json
{
  "id": "pc1…",
  "global_product_id": "<id>",
  "global_category_id": "<id ANALGESICOS>",
  "is_primary": true,
  "status": "ACTIVE",
  "version": 1,
  "…": "…"
}
```

- La **primera** categoría queda como principal automáticamente; las siguientes no.
- Se puede asignar cualquier categoría activa, sea o no hoja del árbol.
- Si la pareja existía inactiva, se reactiva la misma asociación (respuesta `200`) **sin volver a
  ser principal**.
- Ya asignada y activa → `409 DUPLICATE_ASSOCIATION`; categoría inactiva → `422 REFERENCE_INACTIVE`.

### POST `…/set-primary` — Cambiar la principal

```http
POST /api/v1/products/<id>/categories/pc2…/set-primary
{ "version": 1 }
```

Desmarca la anterior y marca esta en una sola operación. Devuelve la lista completa de categorías del
producto.

### POST `…/deactivate` — Retirar una categoría

```http
POST /api/v1/products/<id>/categories/pc1…/deactivate
{ "version": 1, "new_primary_association_id": "pc2…" }
```

- Si se retira la **principal** y quedan otras, hay que indicar cuál la reemplaza; si no →
  `422 NEW_PRIMARY_REQUIRED`.
- Si era la única, se retira y el producto queda incompleto (`NO_ACTIVE_CATEGORY`).
- Los valores de atributo que dejan de aplicar **no se borran**: quedan "fuera de clasificación".

---

## 2. Valores de atributo — `/api/v1/products/{id}/attribute-values`

| Ruta | Permiso |
| --- | --- |
| `GET …/attribute-values` | `products:read` |
| `PUT …/attribute-values/{definition_id}` | `products:update` |
| `DELETE …/attribute-values/{definition_id}?version=n` | `products:delete` |

### PUT — Registrar o reemplazar un valor

Se envía **exactamente un** dato, en el campo que corresponde al tipo de la definición:

| `data_type` | Campo | Ejemplo | Regla |
| --- | --- | --- | --- |
| `TEXT` | `text_value` | `"Crema tópica"` | No vacío |
| `INTEGER` | `integer_value` | `100` | Entero de 64 bits |
| `DECIMAL` | `decimal_value` | `2.5` | Hasta 10 dígitos enteros y 8 decimales |
| `BOOLEAN` | `boolean_value` | `true` | |
| `DATE` | `date_value` | `"2026-09-25"` | Fecha válida |
| `OPTION` | `option_id` | `"<id opción L>"` | Opción activa de esa misma definición |

Registrar por primera vez (sin `version`):

```http
PUT /api/v1/products/<id>/attribute-values/<id CONCENTRACION_MG>
{ "decimal_value": 500 }
```

Respuesta `201`:

```json
{
  "id": "v1…",
  "global_product_id": "<id>",
  "attribute_definition_id": "<id CONCENTRACION_MG>",
  "option_id": null,
  "text_value": null,
  "integer_value": null,
  "decimal_value": "500.00000000",
  "boolean_value": null,
  "date_value": null,
  "out_of_classification": false,
  "version": 1,
  "…": "…"
}
```

Reemplazar (con `version`) → `200`:

```http
PUT /api/v1/products/<id>/attribute-values/<id CONCENTRACION_MG>
{ "decimal_value": 650, "version": 1 }
```

| Error | Cuándo |
| --- | --- |
| `422 ATTRIBUTE_NOT_APPLICABLE` | Ninguna categoría asignada al producto usa ese atributo |
| `422 VALUE_TYPE_MISMATCH` | Campo equivocado para el tipo, ningún dato o más de uno |
| `422 OPTION_NOT_IN_DEFINITION` | La opción es de otra definición o está inactiva |
| `422 VALUE_OUT_OF_CLASSIFICATION` | El valor quedó fuera de clasificación y se intenta modificar |
| `422 REFERENCE_INACTIVE` | La definición está inactiva |
| `422 VALIDATION_ERROR` | Reemplazo sin `version`, o el dato no se puede convertir (p. ej. `"alto"` como decimal) |
| `409 VERSION_CONFLICT` | La versión no es la vigente |

### GET — Listar valores

Devuelve todos los valores del producto. `out_of_classification: true` indica que su atributo ya no
aplica por ninguna categoría del producto: el valor se conserva, pero no se puede modificar hasta que
vuelva a aplicar.

### DELETE — Retirar un valor

Es la **única eliminación física** del servicio.

```http
DELETE /api/v1/products/<id>/attribute-values/<id CONCENTRACION_MG>?version=2
```

Respuesta `204`. Versión incorrecta → `409 VERSION_CONFLICT`.
