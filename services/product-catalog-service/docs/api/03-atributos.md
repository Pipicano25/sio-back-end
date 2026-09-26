# Atributos: definiciones, opciones y atributos por categoría

Los atributos describen características que no son comunes a todos los productos (concentración,
talla, contenido de grasa…). Se modelan en tres piezas:

1. **Definición**: qué significa la característica y qué tipo de dato admite.
2. **Opciones**: los valores permitidos, solo para definiciones de tipo `OPTION`.
3. **Atributo por categoría**: qué categorías usan la definición, si es obligatoria y si sirve
   para filtrar.

El **valor** concreto de cada producto se registra aparte: ver
[05-clasificacion-y-valores.md](05-clasificacion-y-valores.md).

**Sin herencia:** un atributo asociado a `MEDICAMENTOS` no aplica a los productos de su subcategoría
`GENERICOS`. Si la subcategoría lo necesita, se asocia también a ella.

---

## 1. Definiciones — `/api/v1/attribute-definitions`

Recurso de permiso: `attribute-definitions`.

| Ruta | Permiso |
| --- | --- |
| `GET /attribute-definitions` (paginada: `status`, `code`, `search`, `data_type`) | `read` |
| `GET /attribute-definitions/{id}` | `read` |
| `POST /attribute-definitions` | `create` |
| `PUT /attribute-definitions/{id}` | `update` |
| `POST /attribute-definitions/{id}/deactivate` · `/reactivate` | `deactivate` |

### POST — Crear

| Campo | Obligatorio | Regla |
| --- | --- | --- |
| `code` | Sí | Máx. 80; único |
| `name` | Sí | Máx. 120 |
| `description` | **Sí** | No puede estar vacía: explica el significado |
| `data_type` | Sí | `TEXT`, `INTEGER`, `DECIMAL`, `BOOLEAN`, `DATE` u `OPTION` |
| `unit_of_measure_id` | No | Solo para `INTEGER` y `DECIMAL`; unidad activa |

```http
POST /api/v1/attribute-definitions
{
  "code": "CONCENTRACION_MG",
  "name": "Concentración",
  "description": "Cantidad de principio activo por unidad, en miligramos.",
  "data_type": "DECIMAL",
  "unit_of_measure_id": "<id MG>"
}
```

| Error | Cuándo |
| --- | --- |
| `422 UNIT_NOT_ALLOWED_FOR_DATA_TYPE` | Se envió unidad para un tipo que no es `INTEGER`/`DECIMAL` |
| `422 REFERENCE_INACTIVE` | La unidad está inactiva |
| `409 DUPLICATE_CODE` | El código ya existe |

### PUT — Modificar

Solo `name` y `description`:

```json
{ "name": "Concentración (mg)", "description": "Miligramos de principio activo por unidad.", "version": 1 }
```

`data_type` y `unit_of_measure_id` no se pueden cambiar → `422 IMMUTABLE_FIELD`.

### Inactivar

Una definición inactiva no se puede asociar a categorías nuevas ni recibir valores nuevos, y deja de
contar como obligatoria para la completitud.

---

## 2. Opciones — `/api/v1/attribute-definitions/{id}/options`

Solo para definiciones `OPTION` activas.

| Ruta | Permiso |
| --- | --- |
| `GET …/options` (lista ordenada por `display_order`; filtro `status`) | `attribute-definitions:read` |
| `POST …/options` | `attribute-definitions:update` |
| `PUT …/options/{option_id}` | `attribute-definitions:update` |
| `POST …/options/{option_id}/deactivate` · `/reactivate` | `attribute-definitions:deactivate` |

| Campo | Alta | Modificación | Regla |
| --- | --- | --- | --- |
| `code` | Sí | No | Máx. 80; único **dentro de la definición** |
| `name` | Sí | Sí | Máx. 120 |
| `description` | Opcional | Opcional | |
| `display_order` | Opcional (0) | Sí | Entero ≥ 0 |

```http
POST /api/v1/attribute-definitions/<id TALLA_PANAL>/options
{ "code": "L", "name": "Grande (L)", "display_order": 4 }
```

```json
{ "id": "o4…", "attribute_definition_id": "<id TALLA_PANAL>", "code": "L", "name": "Grande (L)", "description": null, "display_order": 4, "status": "ACTIVE", "version": 1, "…": "…" }
```

| Error | Cuándo |
| --- | --- |
| `422 DEFINITION_NOT_OPTION` | La definición no es de tipo `OPTION` |
| `409 DUPLICATE_CODE` | La definición ya tiene esa opción |

Reactivar una opción exige que su definición esté activa.

---

## 3. Atributos por categoría — `/api/v1/categories/{id}/attributes`

| Ruta | Permiso |
| --- | --- |
| `GET /categories/{id}/attributes` (filtro `status`) | `categories:read` |
| `POST /categories/{id}/attributes` | `categories:update` |
| `PUT /categories/{id}/attributes/{association_id}` | `categories:update` |
| `POST /categories/{id}/attributes/{association_id}/deactivate` · `/reactivate` | `categories:deactivate` |

### POST — Asociar una definición a la categoría

| Campo | Obligatorio | Regla |
| --- | --- | --- |
| `attribute_definition_id` | Sí | Definición activa |
| `is_required` | No (`false`) | Si es obligatorio para que el producto esté completo |
| `is_filterable` | No (`false`) | Si se puede buscar productos por ese valor |
| `display_order` | No (`0`) | Orden sugerido |

```http
POST /api/v1/categories/<id ANALGESICOS>/attributes
{ "attribute_definition_id": "<id CONCENTRACION_MG>", "is_required": true, "is_filterable": true, "display_order": 1 }
```

- Respuesta `201`. Si la pareja existía **inactiva**, se reactiva y la respuesta es `200`.
- Si ya está activa → `409 DUPLICATE_ASSOCIATION`.
- Categoría o definición inactivas → `422 REFERENCE_INACTIVE`.

### PUT — Cambiar obligatoriedad, filtrado u orden

```json
{ "is_required": false, "is_filterable": true, "display_order": 2, "version": 1 }
```

Marcar un atributo como obligatorio **no modifica** los productos: los que no tengan el valor pasan
a estar incompletos y dejan de poder adoptarse hasta que se complete.
