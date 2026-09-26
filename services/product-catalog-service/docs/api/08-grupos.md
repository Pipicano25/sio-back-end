# Grupos

Los grupos son **dimensiones de clasificación adicionales** a las categorías. Permiten conservar
clasificaciones de otros sistemas, como las columnas `Grupo 1` a `Grupo 15` del Excel de productos,
sin agregar columnas al producto.

- **Tipo de grupo**: la dimensión (`GROUP_1`, `GROUP_2`, …, o una nueva como `COLECCION`).
- **Grupo**: un valor de esa dimensión (`MEDICAMENTOS GENERICOS`, `OTC`…). Puede tener jerarquía
  dentro de su tipo, aunque no es obligatoria.
- **Asignación**: qué grupos tiene un producto.

Los grupos **no afectan la completitud**.

---

## 1. Tipos de grupo — `/api/v1/group-types`

Recurso de permiso: `group-types`.

| Ruta | Permiso |
| --- | --- |
| `GET /group-types` (paginada: `status`, `code`, `search`) | `read` |
| `GET /group-types/{id}` | `read` |
| `POST /group-types` | `create` |
| `PUT /group-types/{id}` | `update` |
| `POST /group-types/{id}/deactivate` · `/reactivate` | `deactivate` |

| Campo | Alta | Modificación | Regla |
| --- | --- | --- | --- |
| `code` | Sí | No | Máx. 50; único |
| `name` | Sí | Sí | Máx. 120 |
| `description` | Opcional | Opcional | |
| `allows_multiple` | Opcional (`false`) | Sí | Si un producto puede tener varios grupos vigentes de este tipo |
| `display_order` | Opcional (`0`) | Sí | ≥ 0 |

```http
POST /api/v1/group-types
{ "code": "COLECCION", "name": "Colección", "allows_multiple": true }
```

La carga inicial crea `GROUP_1` a `GROUP_15` con `allows_multiple: false`.

No se puede pasar `allows_multiple` a `false` si algún producto ya tiene varios grupos vigentes de
ese tipo → `422 MULTIPLE_ASSIGNMENTS_EXIST`.

---

## 2. Grupos

| Ruta | Permiso |
| --- | --- |
| `GET /group-types/{id}/groups` (paginada: `status`, `code`, `search`, `parent_group_id`, `root_only`) | `group-types:read` |
| `POST /group-types/{id}/groups` | `group-types:create` |
| `GET /groups/{group_id}` | `group-types:read` |
| `GET /groups/{group_id}/children` | `group-types:read` |
| `GET /groups/{group_id}/ancestors` | `group-types:read` |
| `PUT /groups/{group_id}` | `group-types:update` |
| `POST /groups/{group_id}/deactivate` · `/reactivate` | `group-types:deactivate` |

### POST — Crear un grupo

| Campo | Obligatorio | Regla |
| --- | --- | --- |
| `code` | Sí | Máx. 50; único **dentro del tipo** |
| `name` | Sí | Máx. 160 |
| `description` | No | |
| `parent_group_id` | No | Grupo activo **del mismo tipo** |

```http
POST /api/v1/group-types/<id GROUP_1>/groups
{ "code": "0002", "name": "MEDICAMENTOS GENERICOS" }
```

| Error | Cuándo |
| --- | --- |
| `409 DUPLICATE_CODE` | El tipo ya tiene un grupo con ese código |
| `422 PARENT_OF_OTHER_TYPE` | El padre pertenece a otro tipo |
| `422 REFERENCE_INACTIVE` | El tipo o el padre están inactivos |

### PUT — Modificar o mover

```json
{ "name": "Medicamentos genéricos", "description": null, "parent_group_id": null, "version": 1 }
```

Mismas reglas que las categorías: `PUT` reemplaza (omitir `parent_group_id` lo deja en primer
nivel), sin ciclos (`422 HIERARCHY_CYCLE`), no se inactiva con hijos activos
(`422 HAS_ACTIVE_CHILDREN`) y no se reactiva con el padre o el tipo inactivos.

---

## 3. Grupos del producto — `/api/v1/products/{id}/group-assignments`

| Ruta | Permiso |
| --- | --- |
| `GET …/group-assignments` (filtro `status`) | `products:read` |
| `POST …/group-assignments` | `products:update` |
| `POST …/group-assignments/{assignment_id}/deactivate` · `/reactivate` | `products:deactivate` |

```http
POST /api/v1/products/<id>/group-assignments
{ "global_product_group_id": "<id grupo OTC>" }
```

```json
{ "id": "ga1…", "global_product_id": "<id>", "global_product_group_id": "<id grupo OTC>", "group_type_id": "<id GROUP_2>", "status": "ACTIVE", "version": 1, "…": "…" }
```

- El grupo y su tipo deben estar activos.
- Si el tipo tiene `allows_multiple: false` y el producto ya tiene otro grupo vigente de ese tipo →
  `422 GROUP_TYPE_SINGLE_VALUE`. Para cambiarlo, primero se retira el anterior.
- Si la pareja existía inactiva, se reactiva (`200`); si está activa → `409 DUPLICATE_ASSOCIATION`.
