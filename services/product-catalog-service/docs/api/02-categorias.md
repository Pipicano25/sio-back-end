# Categorías

Las categorías forman un **árbol** común a todas las empresas: por ejemplo
`MEDICAMENTOS > GENERICOS > ANALGESICOS`. Un producto puede estar en varias categorías y en
cualquier nivel del árbol, no solo en las hojas.

Recurso de permiso: `categories`.

| Ruta | Permiso | Uso |
| --- | --- | --- |
| `GET /api/v1/categories` | `read` | Listar (paginada) |
| `GET /api/v1/categories/{id}` | `read` | Consultar una |
| `GET /api/v1/categories/{id}/children` | `read` | Hijas directas (paginada) |
| `GET /api/v1/categories/{id}/descendants` | `read` | Todos los descendientes (paginada) |
| `GET /api/v1/categories/{id}/ancestors` | `read` | Ruta desde la raíz |
| `POST /api/v1/categories` | `create` | Crear |
| `PUT /api/v1/categories/{id}` | `update` | Modificar o mover |
| `POST /api/v1/categories/{id}/deactivate` · `/reactivate` | `deactivate` | Inactivar / reactivar |

Las rutas de **atributos por categoría** (`/categories/{id}/attributes`) se describen en
[03-atributos.md](03-atributos.md).

---

## GET `/api/v1/categories` — Listar

| Parámetro | Descripción |
| --- | --- |
| `status`, `code`, `search` | Filtros comunes |
| `parent_category_id` | Solo las hijas de esa categoría |
| `root_only=true` | Solo las categorías de primer nivel |

```http
GET /api/v1/categories?root_only=true
```

```json
{
  "items": [
    { "id": "a1…", "code": "ALIMENTOS", "name": "Alimentos", "description": null, "parent_category_id": null, "status": "ACTIVE", "version": 1, "…": "…" },
    { "id": "b2…", "code": "MEDICAMENTOS", "name": "Medicamentos", "description": null, "parent_category_id": null, "status": "ACTIVE", "version": 1, "…": "…" }
  ],
  "page": 1, "page_size": 20, "total_records": 2, "total_pages": 1
}
```

## GET `/api/v1/categories/{id}/ancestors` — Ruta de la categoría

Devuelve la lista **ordenada de la raíz a la categoría**, incluida ella misma.

```http
GET /api/v1/categories/<id ANALGESICOS>/ancestors
```

```json
[
  { "code": "MEDICAMENTOS", "name": "Medicamentos", "…": "…" },
  { "code": "GENERICOS", "name": "Genéricos", "…": "…" },
  { "code": "ANALGESICOS", "name": "Analgésicos", "…": "…" }
]
```

`/children` devuelve solo el nivel inmediato; `/descendants` todos los niveles de debajo.

## POST `/api/v1/categories` — Crear

| Campo | Obligatorio | Regla |
| --- | --- | --- |
| `code` | Sí | Máx. 50; único |
| `name` | Sí | Máx. 120 |
| `description` | No | Qué incluye y qué no |
| `parent_category_id` | No | Categoría padre; debe existir y estar activa |

```http
POST /api/v1/categories
{ "code": "ANALGESICOS", "name": "Analgésicos", "parent_category_id": "<id GENERICOS>" }
```

| Error | Cuándo |
| --- | --- |
| `409 DUPLICATE_CODE` | El código ya existe |
| `422 REFERENCE_NOT_FOUND` | El padre no existe |
| `422 REFERENCE_INACTIVE` | El padre está inactivo |

## PUT `/api/v1/categories/{id}` — Modificar o mover

```json
{ "name": "Analgésicos", "description": "Alivio del dolor", "parent_category_id": "<id GENERICOS>", "version": 1 }
```

- Para **mover** la categoría se cambia `parent_category_id`; con `null` pasa a primer nivel.
- Como `PUT` reemplaza, **si no se envía `parent_category_id`, la categoría queda en primer nivel.**
  Envíe siempre el padre actual si no quiere moverla.
- Mover una rama se lleva todo su subárbol.
- Crear un ciclo (A bajo B y B bajo A, directa o indirectamente, o una categoría bajo sí misma) →
  `422 HIERARCHY_CYCLE`.
- `code` no se puede cambiar → `422 IMMUTABLE_FIELD`.

## POST `/api/v1/categories/{id}/deactivate` · `/reactivate`

Cuerpo `{ "version": n }`.

- No se puede inactivar una categoría con hijas activas → `422 HAS_ACTIVE_CHILDREN`. Hay que
  inactivar o mover las hijas primero.
- No se puede reactivar una categoría cuyo padre está inactivo → `422 PARENT_INACTIVE`.
- Una categoría inactiva no se asigna a productos nuevos, pero **los productos que ya la tienen la
  conservan**: sigue contando para su completitud y para sus atributos obligatorios.

```http
POST /api/v1/categories/<id>/deactivate
{ "version": 2 }
```
