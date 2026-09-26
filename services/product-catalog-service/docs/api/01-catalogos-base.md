# Catálogos base: unidades de medida, tipos de empaque y marcas

Son catálogos simples, con código, nombre y estado, que otros elementos del catálogo referencian:

- **Unidad de medida**: la unidad de control del producto (`UND`, `KG`, `ML`…). Es una magnitud.
- **Tipo de empaque**: cómo viene físicamente una presentación (`BOX`, `TUBE`, `BOTTLE`…). No es
  una cantidad.
- **Marca**: la marca comercial del producto. No es el fabricante.

Un código no puede ser a la vez unidad y empaque: `KG` es unidad, `BOX` es empaque.

Las tres siguen el mismo patrón de rutas. Solo cambian los campos.

---

## 1. Unidades de medida — `/api/v1/units-of-measure`

Recurso de permiso: `units-of-measure`.

### GET `/api/v1/units-of-measure` — Listar (paginada)

**Permiso:** `units-of-measure:read`

| Parámetro | Descripción |
| --- | --- |
| `status` | `ACTIVE` o `INACTIVE` |
| `code` | Código exacto (se normaliza: `kg` = `KG`) |
| `search` | Parte del nombre, sin distinguir mayúsculas ni tildes |
| `measurement_type` | `UNIT`, `MASS`, `VOLUME`, `LENGTH` o `AREA` |

```http
GET /api/v1/units-of-measure?measurement_type=MASS&status=ACTIVE
```

```json
{
  "items": [
    {
      "id": "0c7e…",
      "code": "G",
      "name": "Gramo",
      "symbol": "g",
      "measurement_type": "MASS",
      "allows_decimals": true,
      "status": "ACTIVE",
      "version": 1,
      "created_at": "2026-09-25T14:00:00Z",
      "updated_at": "2026-09-25T14:00:00Z",
      "created_by": "system:product-catalog-seed",
      "updated_by": "system:product-catalog-seed"
    }
  ],
  "page": 1, "page_size": 20, "total_records": 2, "total_pages": 1
}
```

### GET `/api/v1/units-of-measure/{id}` — Consultar una

**Permiso:** `units-of-measure:read`. Devuelve la unidad aunque esté inactiva. `404` si no existe.

### POST `/api/v1/units-of-measure` — Crear

**Permiso:** `units-of-measure:create`

| Campo | Obligatorio | Regla |
| --- | --- | --- |
| `code` | Sí | Máx. 20 tras normalizar; único; no puede coincidir con un tipo de empaque |
| `name` | Sí | Máx. 80 |
| `symbol` | Sí | Máx. 16 |
| `measurement_type` | Sí | `UNIT`, `MASS`, `VOLUME`, `LENGTH`, `AREA` |
| `allows_decimals` | Sí | Si la unidad admite cantidades con decimales |

```http
POST /api/v1/units-of-measure
Content-Type: application/json

{ "code": "kg", "name": "Kilogramo", "symbol": "kg", "measurement_type": "MASS", "allows_decimals": true }
```

Respuesta `201`, con cabecera `Location: /api/v1/units-of-measure/{id}` y `"code": "KG"`.

| Error | Cuándo |
| --- | --- |
| `409 DUPLICATE_CODE` | Ya existe `KG` |
| `409 CODE_USED_BY_PACKAGING_TYPE` | Hay un tipo de empaque con ese código |
| `422 VALIDATION_ERROR` | `measurement_type` desconocido, campos vacíos o demasiado largos |

### PUT `/api/v1/units-of-measure/{id}` — Modificar

**Permiso:** `units-of-measure:update`. Solo se modifican `name` y `symbol`.

```json
{ "name": "Kilogramo", "symbol": "kg", "version": 1 }
```

`measurement_type` y `allows_decimals` **no se pueden cambiar** (otros servicios ya pueden tener
cantidades registradas en esa unidad) → `422 IMMUTABLE_FIELD`.

### POST `/api/v1/units-of-measure/{id}/deactivate` · `/reactivate`

**Permiso:** `units-of-measure:deactivate`. Cuerpo: `{ "version": n }`.

Una unidad inactiva no puede asignarse a productos, presentaciones ni atributos nuevos. Los productos
que ya la usan **no cambian y siguen completos**.

### POST `/api/v1/units-of-measure/batch-lookup` — Consultar hasta 100

**Permiso:** `units-of-measure:read`. Pensada para que otros servicios validen unidades.

```http
POST /api/v1/units-of-measure/batch-lookup
{ "ids": ["0c7e…", "ffff…"] }
```

```json
{
  "items": [
    { "id": "0c7e…", "found": true, "status": "ACTIVE", "measurement_type": "MASS", "allows_decimals": true },
    { "id": "ffff…", "found": false, "status": null, "measurement_type": null, "allows_decimals": null }
  ]
}
```

Más de 100 identificadores → `422 BATCH_LIMIT_EXCEEDED`; los repetidos se ignoran.

---

## 2. Tipos de empaque — `/api/v1/packaging-types`

Recurso de permiso: `packaging-types`. Mismas rutas que las unidades (sin `batch-lookup`).

| Ruta | Permiso |
| --- | --- |
| `GET /packaging-types` (paginada: `status`, `code`, `search`) | `read` |
| `GET /packaging-types/{id}` | `read` |
| `POST /packaging-types` | `create` |
| `PUT /packaging-types/{id}` | `update` |
| `POST /packaging-types/{id}/deactivate` · `/reactivate` | `deactivate` |

| Campo | Alta | Modificación | Regla |
| --- | --- | --- | --- |
| `code` | Sí | No | Máx. 50; no puede coincidir con una unidad (`409 CODE_USED_BY_UNIT_OF_MEASURE`) |
| `name` | Sí | Sí | Máx. 120 |
| `description` | Opcional | Opcional | Texto libre |

```http
POST /api/v1/packaging-types
{ "code": "TUBE", "name": "Tubo", "description": "Envase flexible para cremas y geles" }
```

La carga inicial ya crea `BOX`, `BOTTLE`, `TUBE`, `BAG`, `PACK`, `CAN`, `JAR`, `ENVELOPE`, `ROLL` y
`BLISTER`.

---

## 3. Marcas — `/api/v1/brands`

Recurso de permiso: `brands`. Mismas rutas y campos que los tipos de empaque (`code` máx. 50,
`name` máx. 120, `description`).

```http
POST /api/v1/brands
{ "code": "MK", "name": "MK", "description": "Línea de genéricos de Tecnoquímicas" }
```

```http
PUT /api/v1/brands/{id}
{ "name": "MK Genéricos", "description": "Línea de genéricos de Tecnoquímicas", "version": 1 }
```

Inactivar una marca **no modifica** los productos que ya la tienen; solo impide asignarla a nuevos.
