# Guía de uso de la API — Product Catalog Service

Esta guía explica **cómo usar** la API del catálogo global de productos y **qué lógica aplica** en
cada operación. Complementa, no reemplaza, los documentos normativos:

- Contrato completo de rutas: `specs/002-product-catalog-service/contracts/rest-api.md`
- Catálogo de códigos de error: `specs/002-product-catalog-service/contracts/errors.md`
- Registro del primer uso: `specs/002-product-catalog-service/contracts/first-use.md`
- Reglas de negocio y decisiones: `specs/002-product-catalog-service/spec.md`

Con `SIO_DOCS_ENABLED=true`, la documentación interactiva está en `http://localhost:8003/docs`.

Para el detalle de cada ruta, ver la referencia en [api/](api/README.md). Para recorridos completos
con datos reales del Excel de productos, ver [ejemplo/](ejemplo/README.md).

---

## 1. Qué es y qué no es este servicio

El catálogo define **qué es un producto**, igual para todas las empresas de SIO: su nombre, marca,
fabricante, unidad base, categorías, atributos, presentaciones y códigos de barras.

No guarda nada que dependa de una empresa: precios, costos, stock, SKU, códigos internos,
proveedores ni disponibilidad de compra o venta. Si una solicitud trae esos datos (por ejemplo
`company_id` o `sale_price`), se rechaza con `422`. Esa información vive en Commercial Relationship
Service, que **adopta** productos de este catálogo.

```text
                       ┌───────────────────────────────┐
  Administrador ─────▶  Product Catalog Service        ◀──── Commercial Relationship
  del catálogo         │  (catálogo global, 16 tablas) │       (consulta y registra primer uso)
                       └──────────────┬────────────────┘
                                      │ solo al asignar o cambiar el fabricante
                                      ▼
                            Party Identity Service
```

---

## 2. Reglas comunes a todas las rutas

### 2.1 Autenticación y permisos

Toda ruta bajo `/api/v1` exige un token de Keycloak:

```http
Authorization: Bearer <access_token>
```

- Sin token o con token inválido → `401`.
- Con token pero sin el permiso necesario → `403`.

El permiso tiene la forma `perm:product-catalog:{recurso}:{accion}`. Keycloak puede conceder
comodines (`perm:product-catalog:all:all`).

| Recurso                 | Acciones                                           | Cubre                                   |
| ----------------------- | -------------------------------------------------- | --------------------------------------- |
| `units-of-measure`      | `read`, `create`, `update`, `deactivate`           | Unidades de medida                      |
| `packaging-types`       | `read`, `create`, `update`, `deactivate`           | Tipos de empaque                        |
| `brands`                | `read`, `create`, `update`, `deactivate`           | Marcas                                  |
| `categories`            | `read`, `create`, `update`, `deactivate`           | Categorías y sus atributos              |
| `attribute-definitions` | `read`, `create`, `update`, `deactivate`           | Definiciones de atributo y opciones     |
| `group-types`           | `read`, `create`, `update`, `deactivate`           | Tipos de grupo y grupos                 |
| `products`              | `read`, `create`, `update`, `deactivate`, `delete` | Productos y todo lo que cuelga de ellos |
| `first-use`             | `register`, `register-manual`                      | Marca de primer uso                     |

`deactivate` es un permiso **distinto** de `update`: se exige para inactivar o reactivar cualquier
cosa, incluidos los elementos que dependen de un producto (categorías asignadas, presentaciones,
identificadores, grupos, activos). `delete` solo sirve para retirar un valor de atributo.

Las únicas rutas públicas son `GET /health/live`, `GET /health/ready` y, si está habilitada, la
documentación (`/docs`, `/openapi.json`).

### 2.2 Códigos

Todos los `code` (unidades, marcas, categorías, etc.) se **normalizan**: se quitan los espacios de
los extremos y se pasan a mayúsculas. Por eso `" kg "`, `"Kg"` y `"KG"` son el mismo código, y el
segundo en registrarse recibe `409 DUPLICATE_CODE`.

Un código **no se puede cambiar** después de crearse.

### 2.3 Estados: nada se borra

Casi todo tiene `status` = `ACTIVE` o `INACTIVE`. En lugar de borrar se inactiva:

```http
POST /api/v1/brands/{id}/deactivate
POST /api/v1/brands/{id}/reactivate
Content-Type: application/json

{ "version": 3 }
```

Reglas que aplican siempre:

- Un elemento `INACTIVE` **no puede asignarse** a nada nuevo (una marca inactiva no se asigna a un
  producto, una categoría inactiva no se asigna, etc.).
- Inactivar **no se propaga**: los productos que ya usaban una marca inactivada la conservan.
- Reactivar exige que el elemento del que depende esté activo (por ejemplo, el padre de una
  categoría). Las referencias ya asignadas (marca, unidad base, empaque) no se revalidan.
- Al inactivar se pierde la marca de principal o de base (`is_primary`, `is_base`), y reactivar no
  la restaura.

La **única** eliminación física es retirar un valor de atributo
(`DELETE /products/{id}/attribute-values/{definition_id}?version=n`).

### 2.4 Control de versiones (concurrencia optimista)

Cada registro tiene un `version` que sube en cada cambio. Para modificar hay que enviar la versión
que se leyó:

```http
PUT /api/v1/brands/{id}
Content-Type: application/json

{ "name": "Acme S.A.", "description": null, "version": 1 }
```

Si otra persona lo modificó antes, la versión ya no coincide y la respuesta es
`409 VERSION_CONFLICT`: hay que volver a leer el registro y reintentar.

### 2.5 Modificaciones (`PUT`)

El cuerpo de `PUT` lleva **solo los campos modificables** más `version`. Si incluye un campo que no
se puede cambiar (por ejemplo `code`, `data_type` o `product_type`), la respuesta es
`422 IMMUTABLE_FIELD`. Tampoco se aceptan campos desconocidos ni de auditoría (`created_by`,
`updated_by`): la auditoría la pone el servicio con el `sub` del token.

### 2.6 Listados y paginación

Los listados aceptan `page` (desde 1) y `page_size` (1 a 100, por defecto 20) y responden:

```json
{
  "items": [ ... ],
  "page": 1,
  "page_size": 20,
  "total_records": 57,
  "total_pages": 3
}
```

Filtros comunes: `status` (`ACTIVE`/`INACTIVE`), `code` (exacto) y `search` (parte del nombre, sin
distinguir mayúsculas ni tildes: `search=cafe` encuentra "Café molido").

### 2.7 Errores

Todos los errores usan el formato RFC 9457 (`application/problem+json`):

```json
{
  "type": "https://sio/errors/product-catalog/version-conflict",
  "title": "Versión desactualizada",
  "status": 409,
  "detail": "El registro fue modificado por otra operación; consulte la versión vigente.",
  "instance": "/api/v1/brands/5f0c…",
  "code": "PRODUCT_CATALOG.VERSION_CONFLICT",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736"
}
```

| Estado | Cuándo                                                                    |
| ------ | ------------------------------------------------------------------------- |
| `400`  | El JSON no se puede leer o un parámetro de la URL no se puede interpretar |
| `401`  | Falta el token o no es válido                                             |
| `403`  | Falta el permiso (o Party Identity negó la consulta del fabricante)       |
| `404`  | El recurso de la ruta no existe                                           |
| `409`  | Código duplicado, colisión de código de barras o versión desactualizada   |
| `422`  | Datos inválidos o una regla de negocio no se cumple                       |
| `503`  | Party Identity no está disponible                                         |

Usa siempre el campo `code` para decidir qué hacer; el texto de `detail` puede cambiar.

### 2.8 Trazabilidad

Toda respuesta trae la cabecera `X-Trace-Id`, que también aparece en los errores y en los logs del
servicio. Si envías una cabecera W3C `traceparent`, se reutiliza su identificador.

---

## 3. Recorrido completo: de cero a un producto adoptable

Este es el orden natural para cargar un producto. Los identificadores son de ejemplo.

### Paso 0 — Catálogos base

Las unidades de medida, los tipos de empaque y los tipos de grupo `GROUP_1` a `GROUP_15` se cargan
con `python -m product_catalog_service.seed load`. También se pueden crear por la API:

```http
POST /api/v1/units-of-measure
{ "code": "KG", "name": "Kilogramo", "symbol": "kg", "measurement_type": "MASS", "allows_decimals": true }
```

- `measurement_type`: `UNIT`, `MASS`, `VOLUME`, `LENGTH` o `AREA`.
- `measurement_type` y `allows_decimals` no se pueden cambiar después (otros servicios ya pueden
  tener cantidades registradas con esa unidad).
- Un tipo de empaque no puede tener el mismo código que una unidad, y al revés: `KG` es una unidad,
  `BOX` es un empaque.

### Paso 1 — Categorías

Las categorías forman un árbol:

```http
POST /api/v1/categories
{ "code": "ALIMENTOS", "name": "Alimentos" }

POST /api/v1/categories
{ "code": "LACTEOS", "name": "Lácteos", "parent_category_id": "<id ALIMENTOS>" }

POST /api/v1/categories
{ "code": "LECHES", "name": "Leches", "parent_category_id": "<id LACTEOS>" }
```

Lógica del árbol:

- No se permiten ciclos: mover `ALIMENTOS` bajo `LECHES` → `422 HIERARCHY_CYCLE`.
- No se puede inactivar una categoría con hijas activas → `422 HAS_ACTIVE_CHILDREN`.
- Consultas útiles: `GET /categories/{id}/children`, `/descendants` y `/ancestors` (la ruta desde la
  raíz, por ejemplo Alimentos > Lácteos > Leches).
- Se puede asignar un producto a cualquier nivel del árbol, no solo a las hojas.

### Paso 2 — Atributos y qué categorías los usan

Una **definición de atributo** dice qué significa una característica y su tipo de dato:

```http
POST /api/v1/attribute-definitions
{
  "code": "PORCENTAJE_GRASA",
  "name": "Porcentaje de grasa",
  "description": "Contenido graso del producto en porcentaje.",
  "data_type": "DECIMAL"
}
```

- `data_type`: `TEXT`, `INTEGER`, `DECIMAL`, `BOOLEAN`, `DATE` u `OPTION`.
- Solo `INTEGER` y `DECIMAL` admiten `unit_of_measure_id`.
- `data_type` y la unidad no se pueden cambiar después.

Para `OPTION` se definen las opciones permitidas:

```http
POST /api/v1/attribute-definitions/{id COLOR}/options
{ "code": "RED", "name": "Rojo", "display_order": 1 }
```

Luego se dice **qué categoría usa qué atributo**:

```http
POST /api/v1/categories/{id LECHES}/attributes
{ "attribute_definition_id": "<id PORCENTAJE_GRASA>", "is_required": true, "is_filterable": true, "display_order": 1 }
```

- `is_required`: el producto no estará completo sin ese valor.
- `is_filterable`: se puede buscar productos por ese valor.
- **No hay herencia**: un atributo de `LACTEOS` no aplica automáticamente a los productos de
  `LECHES`. Si la subcategoría lo necesita, se asocia también a ella.

### Paso 3 — Marca y producto

```http
POST /api/v1/brands
{ "code": "ALPINA", "name": "Alpina" }

POST /api/v1/products
{
  "product_type": "GOOD",
  "canonical_name": "Leche entera 1 L",
  "description": "Leche de vaca entera",
  "global_brand_id": "<id ALPINA>",
  "manufacturer_organization_id": "<id de la organización en Party Identity>",
  "base_unit_id": "<id UND>"
}
```

Lo que ocurre al crear:

- Marca y unidad base deben existir y estar activas.
- **Fabricante**: es opcional. Si se envía, el servicio pregunta a Party Identity si la
  organización existe:
  - no existe → `422 MANUFACTURER_NOT_FOUND`;
  - Party Identity niega el acceso al usuario → `403 MANUFACTURER_ACCESS_DENIED`;
  - Party Identity no responde → `503 DEPENDENCY_UNAVAILABLE` (reintentar más tarde).

  Al modificar el producto solo se vuelve a preguntar si el fabricante **cambia**. Editar la
  descripción, reenviar el mismo fabricante o quitarlo no depende de Party Identity.

- **Posibles duplicados**: si ya existe otro producto con el mismo nombre (sin importar mayúsculas,
  tildes ni espacios repetidos) y la misma marca, el producto se crea igual, pero la respuesta trae
  una advertencia:

  ```json
  "warnings": [
    {
      "code": "POSSIBLE_DUPLICATE",
      "message": "Existe otro producto con el mismo nombre normalizado y la misma marca.",
      "matching_product_ids": ["7c1e…"]
    }
  ]
  ```

  Nunca bloquea: revisar y decidir es trabajo del administrador.

El producto recién creado está `ACTIVE` pero **incompleto**: ver la sección 4.

### Paso 4 — Clasificar el producto

```http
POST /api/v1/products/{id}/categories
{ "global_category_id": "<id LECHES>" }
```

- La primera categoría queda como **principal** automáticamente.
- Siempre hay exactamente una principal mientras el producto tenga categorías. Para cambiarla:
  `POST /products/{id}/categories/{asociacion}/set-primary` con `{ "version": n }`.
- Para retirar la principal cuando hay otras, hay que indicar cuál la reemplaza:

  ```json
  { "version": 1, "new_primary_association_id": "<otra asociación>" }
  ```

  Sin eso → `422 NEW_PRIMARY_REQUIRED`.

- Volver a asignar una categoría retirada reactiva la misma asociación (respuesta `200`).

### Paso 5 — Valores de atributo

```http
PUT /api/v1/products/{id}/attribute-values/{id PORCENTAJE_GRASA}
{ "decimal_value": 3.5 }
```

- Se envía **exactamente un** dato, en el campo que corresponde al tipo: `text_value`,
  `integer_value`, `decimal_value`, `boolean_value`, `date_value` u `option_id`. Otro campo o dos
  campos → `422 VALUE_TYPE_MISMATCH`.
- El atributo debe ser **aplicable**: lo usa alguna categoría asignada al producto. Si no →
  `422 ATTRIBUTE_NOT_APPLICABLE`.
- Para `OPTION`, la opción debe ser activa y de esa misma definición → si no,
  `422 OPTION_NOT_IN_DEFINITION`.
- El primer `PUT` crea el valor (`201`); los siguientes lo reemplazan y deben llevar `version`
  (`200`).
- Un producto tiene como máximo **un valor por atributo**.
- Si se retira la categoría que hacía aplicable un atributo, el valor **no se borra**: queda marcado
  `out_of_classification: true` y no se puede modificar hasta que el atributo vuelva a aplicar.
- Retirar un valor lo borra: `DELETE …/attribute-values/{definition_id}?version=n` → `204`.

Para saber qué atributos le aplican a un producto:
`GET /api/v1/products/{id}/applicable-attributes`.

### Paso 6 — Presentaciones

```http
POST /api/v1/products/{id}/presentations
{
  "code": "CAJA_X_12",
  "name": "Caja x 12 unidades",
  "packaging_type_id": "<id BOX>",
  "base_quantity": 12,
  "display_order": 2,
  "is_base": false
}
```

- `base_quantity` dice cuántas unidades base equivalen a una presentación (una caja = 12 unidades).
  Debe ser mayor que cero.
- `content_quantity` y `content_unit_id` van juntos o ninguno (por ejemplo, un frasco de 120 `ML`).
- Puede haber como máximo **una presentación base** activa, y su `base_quantity` debe ser `1`.
- El `code` es único dentro del producto, también entre presentaciones inactivas: no se reutiliza.

### Paso 7 — Códigos de barras

```http
POST /api/v1/products/{id}/identifiers
{
  "identifier_type": "EAN",
  "value": "7702001041024",
  "global_product_presentation_id": "<id CAJA_X_12>",
  "is_primary": true
}
```

Tipos: `GTIN`, `EAN`, `UPC`, `BARCODE`, `OTHER`. La lógica es la parte más estricta del catálogo:

- El valor se guarda como texto, sin espacios ni guiones y **conservando los ceros iniciales**.
- `GTIN`, `EAN` y `UPC` son **una sola familia**: deben ser numéricos, de 8, 12, 13 o 14 dígitos,
  con dígito de control válido. Para comparar se rellenan con ceros hasta 14 dígitos, así que
  `036000291452` (UPC), `0036000291452` (EAN) y `00036000291452` (GTIN) son **el mismo código**.
- Cada código de la familia puede existir **una sola vez en todo el catálogo**, aunque el registro
  anterior esté inactivo. Si ya existe → `409 IDENTIFIER_COLLISION`, con el registro con el que
  choca:

  ```json
  "conflict": {
    "global_product_id": "…",
    "global_product_presentation_id": null,
    "identifier_id": "…",
    "identifier_type": "UPC",
    "status": "INACTIVE"
  }
  ```

  El servicio **nunca** resuelve la colisión por su cuenta: la revisa una persona.

- `BARCODE` es un código escaneable genérico que **no** es GTIN/EAN/UPC. Si el valor cumple ese
  estándar → `422 BARCODE_IS_GTIN` (regístrelo con su tipo correcto). También es único en todo el
  catálogo.
- `OTHER` solo es único dentro de su producto.
- Si se indica una presentación, debe ser del mismo producto.
- Como máximo un identificador principal por tipo y por contexto (el producto o cada presentación).
- Un identificador no se modifica: para corregirlo se inactiva y se registra otro.

Con esto el producto ya está **completo** y es **elegible**.

### Paso 8 (opcional) — Grupos y activos

- **Grupos**: dimensiones extra de clasificación (`GROUP_1`…`GROUP_15`, colecciones…). Si el tipo
  tiene `allows_multiple: false`, un producto solo puede tener un grupo activo de ese tipo
  (`422 GROUP_TYPE_SINGLE_VALUE`). No afectan la completitud.

  ```http
  POST /api/v1/group-types/{id GROUP_1}/groups
  { "code": "LACTEOS", "name": "Lácteos" }

  POST /api/v1/products/{id}/group-assignments
  { "global_product_group_id": "<id grupo>" }
  ```

- **Activos**: referencias a imágenes, fichas técnicas, manuales o certificados guardados fuera del
  servicio. Solo se guarda la URI, nunca el archivo:

  ```http
  POST /api/v1/products/{id}/assets
  { "asset_type": "IMAGE", "file_name": "frente.png", "storage_uri": "s3://sio-assets/leche/frente.png", "mime_type": "image/png", "is_primary": true }
  ```

---

## 4. Completitud y elegibilidad

Son dos ideas distintas del **estado** (`status`):

- `status` dice si el registro está vivo (`ACTIVE`) o retirado (`INACTIVE`).
- **Completitud** dice si la información del producto es suficiente. Se **calcula en cada
  consulta** y nunca se guarda.

Un producto está completo cuando cumple las seis condiciones:

| #   | Condición                                                              | Problema que se informa si falla             |
| --- | ---------------------------------------------------------------------- | -------------------------------------------- |
| 1   | Tiene tipo, nombre y unidad base                                       | `MISSING_MINIMUM_DATA`                       |
| 2   | La unidad base existe (que esté inactiva no importa)                   | `BASE_UNIT_NOT_FOUND`                        |
| 3   | Tiene al menos una categoría y exactamente una principal               | `NO_ACTIVE_CATEGORY` / `NO_PRIMARY_CATEGORY` |
| 4   | Tiene valor para cada atributo obligatorio de **todas** sus categorías | `MISSING_REQUIRED_ATTRIBUTE`                 |
| 5   | Esos valores tienen el tipo correcto                                   | `INCONSISTENT_REQUIRED_VALUE`                |
| 6   | Tiene al menos una presentación activa                                 | `NO_ACTIVE_PRESENTATION`                     |

Cada producto trae el resultado:

```json
"completeness": {
  "is_complete": false,
  "issues": ["MISSING_REQUIRED_ATTRIBUTE", "NO_ACTIVE_PRESENTATION"],
  "missing_attribute_definition_ids": ["…"],
  "out_of_classification_value_ids": []
},
"eligible_for_adoption": false
```

También se puede pedir solo esto: `GET /api/v1/products/{id}/completeness`.

**Elegible para adopción** = `ACTIVE` **y** completo. Una presentación es elegible si está activa y
su producto es elegible.

| `status`   | Completitud | ¿Se puede adoptar? |
| ---------- | ----------- | ------------------ |
| `ACTIVE`   | Completo    | Sí                 |
| `ACTIVE`   | Incompleto  | No                 |
| `INACTIVE` | Cualquiera  | No                 |

Detalles que conviene saber:

- La incompletitud **no impide** crear, editar ni consultar el producto; se completa poco a poco.
- Inactivar una categoría, marca o unidad **no** vuelve incompletos a los productos que ya la
  tenían: solo impide asignarla de nuevo.
- Si se agrega un atributo obligatorio a una categoría, sus productos pasan a incompletos. Las
  adopciones ya hechas en otros servicios no se ven afectadas.

---

## 5. Primer uso: cuándo un producto deja de poder cambiar lo esencial

Mientras nadie ha usado un producto, se pueden corregir su unidad base y los datos físicos de sus
presentaciones. Cuando una empresa lo adopta, esos datos pasan a tener historia (compras, ventas,
inventario) y ya no deben cambiar.

Para eso existe la **marca de primer uso**. La registra el servicio que adopta:

```http
POST /api/v1/products/{id}/first-use
Authorization: Bearer <token de la cuenta de servicio de Commercial Relationship>

{ "global_product_presentation_id": "<id CAJA_X_12>" }
```

Respuesta `200`:

```json
{
  "global_product_id": "…",
  "product_first_used_at": "2026-09-25T15:04:05Z",
  "product_first_use_source": "ADOPTION",
  "global_product_presentation_id": "…",
  "presentation_first_used_at": "2026-09-25T15:04:05Z",
  "presentation_first_use_source": "ADOPTION"
}
```

Lógica:

- Marcar una presentación marca también su producto.
- Es **idempotente**: llamar dos veces no cambia la fecha y responde `200`.
- Si todavía no hay marca, el producto (y la presentación) deben ser elegibles; si no →
  `422 NOT_ELIGIBLE_FOR_FIRST_USE`.
- Es **irreversible**: no existe ninguna ruta para quitarla.
- No guarda datos de la empresa que adopta.
- Un administrador puede registrarla a mano (por ejemplo, para productos migrados que ya se usaban):
  `POST /products/{id}/first-use/manual`, con permiso `first-use:register-manual`. Esta vía no exige
  elegibilidad.

Qué cambia después de la marca:

| Dato                                                                                           | Sin marca          | Con marca                                                               |
| ---------------------------------------------------------------------------------------------- | ------------------ | ----------------------------------------------------------------------- |
| `base_unit_id` del producto                                                                    | Se puede corregir  | `422 BASE_UNIT_LOCKED_BY_FIRST_USE`                                     |
| `packaging_type_id`, `base_quantity`, `content_quantity`, `content_unit_id` de la presentación | Se pueden corregir | `422 PRESENTATION_LOCKED_BY_FIRST_USE` (se crea una presentación nueva) |
| Nombre, descripción, orden, `is_base`                                                          | Se pueden cambiar  | Se pueden cambiar                                                       |

**Obligación del servicio que adopta**: llamar a `first-use` **antes** de confirmar la adopción y
**rechazar** la adopción si la llamada falla. No debe confirmarla sin la marca ni dejarla para
después.

---

## 6. Consultas para otros servicios y para buscar

### 6.1 Búsqueda de productos

```http
GET /api/v1/products?search=leche&category_id=<id LACTEOS>&include_descendants=true&page=1
```

Filtros combinables:

| Parámetro                                              | Efecto                                                                                       |
| ------------------------------------------------------ | -------------------------------------------------------------------------------------------- |
| `search`                                               | Parte del nombre, sin distinguir mayúsculas ni tildes                                        |
| `status`                                               | `ACTIVE` o `INACTIVE`                                                                        |
| `category_id` (+ `include_descendants=true`)           | Productos de la categoría (y de sus subcategorías)                                           |
| `brand_id`, `manufacturer_organization_id`, `group_id` | Por marca, fabricante o grupo                                                                |
| `identifier`                                           | Por código: familia GTIN, `BARCODE` u `OTHER` (este último puede devolver varios productos)  |
| `attribute_filters=CODIGO:valor`                       | Por valor de un atributo filtrable; repetible. Ej.: `attribute_filters=PORCENTAJE_GRASA:3.5` |

Un atributo que no es filtrable en ninguna categoría → `422 ATTRIBUTE_NOT_FILTERABLE`.

### 6.2 Detalle completo

```http
GET /api/v1/products/{id}?expand=detail
```

Agrega `detail` con las categorías, presentaciones, identificadores, valores de atributo, grupos y
activos **vigentes**.

### 6.3 Buscar por código escaneado

```http
GET /api/v1/products/by-identifier/7702001041024
```

Devuelve el producto, la presentación (si el código es de una presentación), el identificador y
`is_current`, que es `true` solo si el identificador, el producto y la presentación están activos.
Resuelve la familia GTIN (cualquier variante de ceros) y `BARCODE`, no `OTHER`.

### 6.4 Consultas por lotes (para validar adopciones)

Hasta 100 identificadores por llamada; los repetidos se ignoran. Más de 100 →
`422 BATCH_LIMIT_EXCEEDED`.

```http
POST /api/v1/products/batch-lookup
{ "ids": ["…", "…"] }
```

```json
{
  "items": [
    {
      "id": "…",
      "found": true,
      "status": "ACTIVE",
      "is_complete": true,
      "eligible_for_adoption": true,
      "first_used_at": null
    },
    {
      "id": "…",
      "found": false,
      "status": null,
      "is_complete": null,
      "eligible_for_adoption": null,
      "first_used_at": null
    }
  ]
}
```

Equivalentes: `POST /api/v1/presentations/batch-lookup` (incluye `code`, `name`, `base_quantity` y la elegibilidad)
y `POST /api/v1/units-of-measure/batch-lookup` (incluye `measurement_type` y `allows_decimals`).

### 6.5 Flujo recomendado para un servicio que adopta

```text
1. POST /products/batch-lookup y /presentations/batch-lookup
      └─ ¿eligible_for_adoption = true?  no → rechazar la adopción
2. POST /products/{id}/first-use  (con la presentación, si aplica)
      └─ ¿200?  no (error, 5xx, tiempo agotado) → rechazar la adopción
3. Confirmar la adopción en el servicio propio
```

---

## 7. Resumen rápido de rutas

| Área                      | Rutas principales                                                                                                                                                 |
| ------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Unidades                  | `GET/POST /units-of-measure`, `GET/PUT /units-of-measure/{id}`, `…/deactivate`, `…/reactivate`, `POST /units-of-measure/batch-lookup`                             |
| Empaques                  | `GET/POST /packaging-types`, `GET/PUT /packaging-types/{id}`, `…/deactivate`, `…/reactivate`                                                                      |
| Marcas                    | `GET/POST /brands`, `GET/PUT /brands/{id}`, `…/deactivate`, `…/reactivate`                                                                                        |
| Categorías                | `GET/POST /categories`, `GET/PUT /categories/{id}`, `…/children`, `…/descendants`, `…/ancestors`, `…/attributes`                                                  |
| Atributos                 | `GET/POST /attribute-definitions`, `GET/PUT /attribute-definitions/{id}`, `…/options`                                                                             |
| Productos                 | `GET/POST /products`, `GET/PUT /products/{id}`, `…/completeness`, `…/applicable-attributes`, `POST /products/batch-lookup`, `GET /products/by-identifier/{value}` |
| Dependientes del producto | `…/categories`, `…/attribute-values/{definition_id}`, `…/presentations`, `…/identifiers`, `…/group-assignments`, `…/assets`                                       |
| Presentaciones            | `GET/PUT /presentations/{id}`, `…/deactivate`, `…/reactivate`, `POST /presentations/batch-lookup`                                                                 |
| Grupos                    | `GET/POST /group-types`, `GET/POST /group-types/{id}/groups`, `GET/PUT /groups/{id}`, `…/children`, `…/ancestors`                                                 |
| Primer uso                | `POST /products/{id}/first-use`, `POST /products/{id}/first-use/manual`                                                                                           |
| Salud                     | `GET /health/live`, `GET /health/ready`                                                                                                                           |

Todas las rutas funcionales llevan el prefijo `/api/v1`. El detalle de cuerpos, respuestas y errores
de cada una está en `specs/002-product-catalog-service/contracts/rest-api.md`.
