# Referencia de la API — Product Catalog Service

Referencia detallada de cada ruta, con su descripción, permiso, cuerpo, respuesta, errores típicos y
un ejemplo de uso. Cada archivo cubre un solo grupo de recursos.

| Archivo | Recursos |
| --- | --- |
| [01-catalogos-base.md](01-catalogos-base.md) | Unidades de medida, tipos de empaque y marcas |
| [02-categorias.md](02-categorias.md) | Árbol de categorías |
| [03-atributos.md](03-atributos.md) | Definiciones de atributo, opciones y atributos por categoría |
| [04-productos.md](04-productos.md) | Producto: alta, modificación, búsqueda, detalle, completitud y consultas por lotes |
| [05-clasificacion-y-valores.md](05-clasificacion-y-valores.md) | Categorías de un producto y valores de atributo |
| [06-presentaciones.md](06-presentaciones.md) | Presentaciones físicas del producto |
| [07-identificadores.md](07-identificadores.md) | Códigos de barras y otros identificadores |
| [08-grupos.md](08-grupos.md) | Tipos de grupo, grupos y asignación a productos |
| [09-activos.md](09-activos.md) | Imágenes, fichas técnicas y otros archivos |
| [10-primer-uso.md](10-primer-uso.md) | Marca de primer uso |
| [11-salud.md](11-salud.md) | Comprobaciones de salud |

Documentos relacionados:

- Conceptos y lógica transversal (completitud, primer uso, códigos de barras, errores):
  [../api-guide.md](../api-guide.md)
- Ejercicios paso a paso con datos reales de `docs/CAMPOS PRODUCTOS.xlsx`: [../ejemplo/](../ejemplo/README.md)
- Contrato normativo: `specs/002-product-catalog-service/contracts/rest-api.md`

## Convenciones de estos documentos

- Todas las rutas funcionales empiezan por `/api/v1`. En los ejemplos se usa
  `http://localhost:8003` como servidor.
- Todas llevan `Authorization: Bearer <token>`. Se omite en los ejemplos para acortarlos.
- `{id}` y los valores `<…>` son identificadores UUID de ejemplo.
- **Permiso** indica la parte `{recurso}:{accion}` de `perm:product-catalog:{recurso}:{accion}`.
- Los campos de lectura comunes (`id`, `status`, `version`, `created_at`, `updated_at`,
  `created_by`, `updated_by`) aparecen en todas las respuestas; en los ejemplos se abrevian con
  `"…"` cuando no aportan.

## Reglas que se repiten en todas las rutas

| Regla | Efecto |
| --- | --- |
| Códigos normalizados | `code` se guarda sin espacios extremos y en mayúsculas; no se puede cambiar después. |
| `PUT` reemplaza | El cuerpo lleva **todos** los campos modificables. Un campo opcional que no se envía queda en `null` (por ejemplo, omitir `description` la borra). |
| Campos inmutables | Enviar un campo que no se puede modificar → `422 IMMUTABLE_FIELD`. |
| Campos desconocidos | Cualquier campo que no esté documentado → `422 VALIDATION_ERROR`. |
| Versión | `PUT`, `deactivate`, `reactivate`, `set-primary` y el `DELETE` exigen la versión leída; si no coincide → `409 VERSION_CONFLICT`. |
| Inactivar ≠ borrar | Nada se borra salvo los valores de atributo. |
| Permiso `deactivate` | Inactivar y reactivar exige `deactivate` del recurso dueño, no `update`. |
| Errores | `application/problem+json` con `code` y `trace_id` (ver `api-guide.md` §2.7). |

## Paginación

Las rutas marcadas como "paginada" aceptan `page` (≥ 1, por defecto 1) y `page_size` (1–100, por
defecto 20) y responden:

```json
{ "items": [], "page": 1, "page_size": 20, "total_records": 0, "total_pages": 0 }
```
