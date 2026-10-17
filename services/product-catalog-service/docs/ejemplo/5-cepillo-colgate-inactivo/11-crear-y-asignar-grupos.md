# Paso 11 de 14 — Crear y asignar los grupos

Ejercicio 5 — Cepillo Colgate infantil pack x 2 (producto inactivo) · [← Paso anterior](10-agregar-imagen.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](12-inactivar-producto.md)

**Objetivo:** Conservar la agrupación del sistema anterior.

**Necesita (de pasos anteriores):** `<GT_GROUP_1>`, `<PRODUCTO>`, `<GT_GROUP_2>`, `<GT_GROUP_4>` — pasos [01](01-consultar-datos-base.md), [06](06-crear-producto.md)

**Deja guardado para los siguientes pasos:** `<GRUPO1_0005>`, `<ASIG_GRUPO1>`, `<GRUPO2_0016>`, `<ASIG_GRUPO2>`, `<GRUPO4_0213>`, `<ASIG_GRUPO4>`

`0005` y `0016` también los usa el ejercicio 4. Si ya lo ejecutó, la consulta los encuentra y **no** se crean de nuevo.

**Nota de calidad de datos:** el Excel clasifica este cepillo en `MEDICO QUIRURGICOS / DISPOSITIVOS MEDICOS`, lo cual no es correcto. Los grupos se importan tal como vienen porque representan la agrupación del sistema anterior; la clasificación correcta la da la **categoría** (`CEPILLOS_DENTALES`). Corregir los grupos es una decisión del negocio: se puede hacer después inactivando la asignación (`POST /products/{id}/group-assignments/{id}/deactivate`).

---

## 1. Grupo 1 `0005` — consultar si ya existe

```http
GET /api/v1/group-types/<GT_GROUP_1>/groups?code=0005
```

**Permiso que exige la URL:** `perm:product-catalog:group-types:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:product-catalog:all:read`), `ventas.test` (por `perm:product-catalog:all:read`), `inventario.test` (por `perm:product-catalog:all:read`), `reportes.test` (por `perm:product-catalog:group-types:read`), `consulta.test` (por `perm:product-catalog:group-types:read`)

**Por qué se hace así**

- Los grupos son compartidos por muchos productos: `0005` puede existir porque otro producto (u otro ejercicio) ya lo creó. Se consulta primero para **reutilizarlo** y no intentar duplicarlo (un segundo `POST` con el mismo código responde `409 DUPLICATE_CODE`).

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [],
  "total_records": 0
}
```

**Si `items` trae el grupo:** guarde `items[0].id` → `<GRUPO1_0005>` y **salte** la llamada siguiente (crear). **Si viene vacío** (como en la respuesta de arriba, en una base nueva): haga la llamada siguiente.

## 2. Grupo 1 `0005` — crearlo (solo si la consulta vino vacía)

> **Solo si la consulta anterior devolvió `"items": []`.** Si el grupo ya existía, **omita esta llamada** y use como `<GRUPO1_0005>` el `id` que devolvió la consulta.

```http
POST /api/v1/group-types/<GT_GROUP_1>/groups
```

```json
{
  "code": "0005",
  "name": "Médico quirúrgicos"
}
```

**Permiso que exige la URL:** `perm:product-catalog:group-types:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `create`
- ℹ️ Los grupos se crean dentro de su tipo de grupo: exige `create` sobre `group-types`.

**Por qué se hace así**

- `code` conserva el código del Excel (`0005`) para poder rastrear el origen del dato.
- `name` es el nombre del Excel escrito de forma legible.
- No se envía `parent_group_id`: en el Excel los grupos no tienen jerarquía.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<GRUPO1_0005>",
  "group_type_id": "<GT_GROUP_1>",
  "code": "0005",
  "name": "Médico quirúrgicos",
  "status": "ACTIVE"
}
```

**Guardar:** `id` → `<GRUPO1_0005>`

## 3. Grupo 1 `0005` — asignarlo al producto

```http
POST /api/v1/products/<PRODUCTO>/group-assignments
```

```json
{
  "global_product_group_id": "<GRUPO1_0005>"
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Todo lo que se agrega **dentro** de un producto (categorías, valores, presentaciones, códigos, grupos, imágenes) exige `update` sobre `products`.

**Por qué se hace así**

- `<GRUPO1_0005>` es el `id` del grupo: el de la consulta si ya existía, o el del `POST` si se acaba de crear.
- `GROUP_1` no admite varios grupos (`allows_multiple: false`): el producto queda con un solo grupo de este tipo; un segundo daría `422 GROUP_TYPE_SINGLE_VALUE`.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<ASIG_GRUPO1>",
  "global_product_group_id": "<GRUPO1_0005>",
  "group_type_id": "<GT_GROUP_1>",
  "status": "ACTIVE"
}
```

**Guardar:** `id` → `<ASIG_GRUPO1>`

## 4. Grupo 2 `0016` — consultar si ya existe

```http
GET /api/v1/group-types/<GT_GROUP_2>/groups?code=0016
```

**Permiso que exige la URL:** `perm:product-catalog:group-types:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:product-catalog:all:read`), `ventas.test` (por `perm:product-catalog:all:read`), `inventario.test` (por `perm:product-catalog:all:read`), `reportes.test` (por `perm:product-catalog:group-types:read`), `consulta.test` (por `perm:product-catalog:group-types:read`)

**Por qué se hace así**

- Los grupos son compartidos por muchos productos: `0016` puede existir porque otro producto (u otro ejercicio) ya lo creó. Se consulta primero para **reutilizarlo** y no intentar duplicarlo (un segundo `POST` con el mismo código responde `409 DUPLICATE_CODE`).

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [],
  "total_records": 0
}
```

**Si `items` trae el grupo:** guarde `items[0].id` → `<GRUPO2_0016>` y **salte** la llamada siguiente (crear). **Si viene vacío** (como en la respuesta de arriba, en una base nueva): haga la llamada siguiente.

## 5. Grupo 2 `0016` — crearlo (solo si la consulta vino vacía)

> **Solo si la consulta anterior devolvió `"items": []`.** Si el grupo ya existía, **omita esta llamada** y use como `<GRUPO2_0016>` el `id` que devolvió la consulta.

```http
POST /api/v1/group-types/<GT_GROUP_2>/groups
```

```json
{
  "code": "0016",
  "name": "Dispositivos médicos"
}
```

**Permiso que exige la URL:** `perm:product-catalog:group-types:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `create`
- ℹ️ Los grupos se crean dentro de su tipo de grupo: exige `create` sobre `group-types`.

**Por qué se hace así**

- `code` conserva el código del Excel (`0016`) para poder rastrear el origen del dato.
- `name` es el nombre del Excel escrito de forma legible.
- No se envía `parent_group_id`: en el Excel los grupos no tienen jerarquía.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<GRUPO2_0016>",
  "group_type_id": "<GT_GROUP_2>",
  "code": "0016",
  "name": "Dispositivos médicos",
  "status": "ACTIVE"
}
```

**Guardar:** `id` → `<GRUPO2_0016>`

## 6. Grupo 2 `0016` — asignarlo al producto

```http
POST /api/v1/products/<PRODUCTO>/group-assignments
```

```json
{
  "global_product_group_id": "<GRUPO2_0016>"
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Todo lo que se agrega **dentro** de un producto (categorías, valores, presentaciones, códigos, grupos, imágenes) exige `update` sobre `products`.

**Por qué se hace así**

- `<GRUPO2_0016>` es el `id` del grupo: el de la consulta si ya existía, o el del `POST` si se acaba de crear.
- `GROUP_2` no admite varios grupos (`allows_multiple: false`): el producto queda con un solo grupo de este tipo; un segundo daría `422 GROUP_TYPE_SINGLE_VALUE`.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<ASIG_GRUPO2>",
  "global_product_group_id": "<GRUPO2_0016>",
  "group_type_id": "<GT_GROUP_2>",
  "status": "ACTIVE"
}
```

**Guardar:** `id` → `<ASIG_GRUPO2>`

## 7. Grupo 4 `0213` — consultar si ya existe

```http
GET /api/v1/group-types/<GT_GROUP_4>/groups?code=0213
```

**Permiso que exige la URL:** `perm:product-catalog:group-types:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:product-catalog:all:read`), `ventas.test` (por `perm:product-catalog:all:read`), `inventario.test` (por `perm:product-catalog:all:read`), `reportes.test` (por `perm:product-catalog:group-types:read`), `consulta.test` (por `perm:product-catalog:group-types:read`)

**Por qué se hace así**

- Los grupos son compartidos por muchos productos: `0213` puede existir porque otro producto (u otro ejercicio) ya lo creó. Se consulta primero para **reutilizarlo** y no intentar duplicarlo (un segundo `POST` con el mismo código responde `409 DUPLICATE_CODE`).

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [],
  "total_records": 0
}
```

**Si `items` trae el grupo:** guarde `items[0].id` → `<GRUPO4_0213>` y **salte** la llamada siguiente (crear). **Si viene vacío** (como en la respuesta de arriba, en una base nueva): haga la llamada siguiente.

## 8. Grupo 4 `0213` — crearlo (solo si la consulta vino vacía)

> **Solo si la consulta anterior devolvió `"items": []`.** Si el grupo ya existía, **omita esta llamada** y use como `<GRUPO4_0213>` el `id` que devolvió la consulta.

```http
POST /api/v1/group-types/<GT_GROUP_4>/groups
```

```json
{
  "code": "0213",
  "name": "Colgate-Palmolive"
}
```

**Permiso que exige la URL:** `perm:product-catalog:group-types:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `create`
- ℹ️ Los grupos se crean dentro de su tipo de grupo: exige `create` sobre `group-types`.

**Por qué se hace así**

- `code` conserva el código del Excel (`0213`) para poder rastrear el origen del dato.
- `name` es el nombre del Excel escrito de forma legible.
- No se envía `parent_group_id`: en el Excel los grupos no tienen jerarquía.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<GRUPO4_0213>",
  "group_type_id": "<GT_GROUP_4>",
  "code": "0213",
  "name": "Colgate-Palmolive",
  "status": "ACTIVE"
}
```

**Guardar:** `id` → `<GRUPO4_0213>`

## 9. Grupo 4 `0213` — asignarlo al producto

```http
POST /api/v1/products/<PRODUCTO>/group-assignments
```

```json
{
  "global_product_group_id": "<GRUPO4_0213>"
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Todo lo que se agrega **dentro** de un producto (categorías, valores, presentaciones, códigos, grupos, imágenes) exige `update` sobre `products`.

**Por qué se hace así**

- `<GRUPO4_0213>` es el `id` del grupo: el de la consulta si ya existía, o el del `POST` si se acaba de crear.
- `GROUP_4` no admite varios grupos (`allows_multiple: false`): el producto queda con un solo grupo de este tipo; un segundo daría `422 GROUP_TYPE_SINGLE_VALUE`.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<ASIG_GRUPO4>",
  "global_product_group_id": "<GRUPO4_0213>",
  "group_type_id": "<GT_GROUP_4>",
  "status": "ACTIVE"
}
```

**Guardar:** `id` → `<ASIG_GRUPO4>`

---

[← Paso anterior](10-agregar-imagen.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](12-inactivar-producto.md)
