# Paso 11 de 12 — Crear y asignar los grupos

Ejercicio 2 — Leche NAN 1 Optipro: tres filas del Excel, un solo producto · [← Paso anterior](10-registrar-codigos-de-barras.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](12-verificar-resultado.md)

**Objetivo:** Importar solo los grupos que agrupan algo.

**Necesita (de pasos anteriores):** `<GT_GROUP_1>`, `<PRODUCTO>`, `<GT_GROUP_2>`, `<GT_GROUP_4>` — pasos [01](01-consultar-datos-base.md), [06](06-crear-producto.md)

**Deja guardado para los siguientes pasos:** `<GRUPO1_0687>`, `<ASIG_GRUPO1>`, `<GRUPO2_0689>`, `<ASIG_GRUPO2>`, `<GRUPO4_0336>`, `<ASIG_GRUPO4>`

Las tres filas del Excel tienen los mismos grupos, así que se asignan **una sola vez** al producto.

No se importan:

- `Grupo 3 = 0133 NO APLICA` y `Grupo 5 = 0695 NO APLICA`: no agrupan nada.
- `Grupo 6 = 0836 EXCLUIR VIERNES DAO`: es una **regla comercial** de una empresa (excluir de una promoción los viernes), no una característica del producto. Va en Commercial Relationship Service.

---

## 1. Grupo 1 `0687` — consultar si ya existe

```http
GET /api/v1/group-types/<GT_GROUP_1>/groups?code=0687
```

**Permiso que exige la URL:** `perm:product-catalog:group-types:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:product-catalog:all:read`), `ventas.test` (por `perm:product-catalog:all:read`), `inventario.test` (por `perm:product-catalog:all:read`), `reportes.test` (por `perm:product-catalog:group-types:read`), `consulta.test` (por `perm:product-catalog:group-types:read`)

**Por qué se hace así**

- Los grupos son compartidos por muchos productos: `0687` puede existir porque otro producto (u otro ejercicio) ya lo creó. Se consulta primero para **reutilizarlo** y no intentar duplicarlo (un segundo `POST` con el mismo código responde `409 DUPLICATE_CODE`).

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [],
  "total_records": 0
}
```

**Si `items` trae el grupo:** guarde `items[0].id` → `<GRUPO1_0687>` y **salte** la llamada siguiente (crear). **Si viene vacío** (como en la respuesta de arriba, en una base nueva): haga la llamada siguiente.

## 2. Grupo 1 `0687` — crearlo (solo si la consulta vino vacía)

> **Solo si la consulta anterior devolvió `"items": []`.** Si el grupo ya existía, **omita esta llamada** y use como `<GRUPO1_0687>` el `id` que devolvió la consulta.

```http
POST /api/v1/group-types/<GT_GROUP_1>/groups
```

```json
{
  "code": "0687",
  "name": "Alimentos"
}
```

**Permiso que exige la URL:** `perm:product-catalog:group-types:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `create`
- ℹ️ Los grupos se crean dentro de su tipo de grupo: exige `create` sobre `group-types`.

**Por qué se hace así**

- `code` conserva el código del Excel (`0687`) para poder rastrear el origen del dato.
- `name` es el nombre del Excel escrito de forma legible.
- No se envía `parent_group_id`: en el Excel los grupos no tienen jerarquía.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<GRUPO1_0687>",
  "group_type_id": "<GT_GROUP_1>",
  "code": "0687",
  "name": "Alimentos",
  "status": "ACTIVE"
}
```

**Guardar:** `id` → `<GRUPO1_0687>`

## 3. Grupo 1 `0687` — asignarlo al producto

```http
POST /api/v1/products/<PRODUCTO>/group-assignments
```

```json
{
  "global_product_group_id": "<GRUPO1_0687>"
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Todo lo que se agrega **dentro** de un producto (categorías, valores, presentaciones, códigos, grupos, imágenes) exige `update` sobre `products`.

**Por qué se hace así**

- `<GRUPO1_0687>` es el `id` del grupo: el de la consulta si ya existía, o el del `POST` si se acaba de crear.
- `GROUP_1` no admite varios grupos (`allows_multiple: false`): el producto queda con un solo grupo de este tipo; un segundo daría `422 GROUP_TYPE_SINGLE_VALUE`.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<ASIG_GRUPO1>",
  "global_product_group_id": "<GRUPO1_0687>",
  "group_type_id": "<GT_GROUP_1>",
  "status": "ACTIVE"
}
```

**Guardar:** `id` → `<ASIG_GRUPO1>`

## 4. Grupo 2 `0689` — consultar si ya existe

```http
GET /api/v1/group-types/<GT_GROUP_2>/groups?code=0689
```

**Permiso que exige la URL:** `perm:product-catalog:group-types:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:product-catalog:all:read`), `ventas.test` (por `perm:product-catalog:all:read`), `inventario.test` (por `perm:product-catalog:all:read`), `reportes.test` (por `perm:product-catalog:group-types:read`), `consulta.test` (por `perm:product-catalog:group-types:read`)

**Por qué se hace así**

- Los grupos son compartidos por muchos productos: `0689` puede existir porque otro producto (u otro ejercicio) ya lo creó. Se consulta primero para **reutilizarlo** y no intentar duplicarlo (un segundo `POST` con el mismo código responde `409 DUPLICATE_CODE`).

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [],
  "total_records": 0
}
```

**Si `items` trae el grupo:** guarde `items[0].id` → `<GRUPO2_0689>` y **salte** la llamada siguiente (crear). **Si viene vacío** (como en la respuesta de arriba, en una base nueva): haga la llamada siguiente.

## 5. Grupo 2 `0689` — crearlo (solo si la consulta vino vacía)

> **Solo si la consulta anterior devolvió `"items": []`.** Si el grupo ya existía, **omita esta llamada** y use como `<GRUPO2_0689>` el `id` que devolvió la consulta.

```http
POST /api/v1/group-types/<GT_GROUP_2>/groups
```

```json
{
  "code": "0689",
  "name": "Leches"
}
```

**Permiso que exige la URL:** `perm:product-catalog:group-types:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `create`
- ℹ️ Los grupos se crean dentro de su tipo de grupo: exige `create` sobre `group-types`.

**Por qué se hace así**

- `code` conserva el código del Excel (`0689`) para poder rastrear el origen del dato.
- `name` es el nombre del Excel escrito de forma legible.
- No se envía `parent_group_id`: en el Excel los grupos no tienen jerarquía.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<GRUPO2_0689>",
  "group_type_id": "<GT_GROUP_2>",
  "code": "0689",
  "name": "Leches",
  "status": "ACTIVE"
}
```

**Guardar:** `id` → `<GRUPO2_0689>`

## 6. Grupo 2 `0689` — asignarlo al producto

```http
POST /api/v1/products/<PRODUCTO>/group-assignments
```

```json
{
  "global_product_group_id": "<GRUPO2_0689>"
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Todo lo que se agrega **dentro** de un producto (categorías, valores, presentaciones, códigos, grupos, imágenes) exige `update` sobre `products`.

**Por qué se hace así**

- `<GRUPO2_0689>` es el `id` del grupo: el de la consulta si ya existía, o el del `POST` si se acaba de crear.
- `GROUP_2` no admite varios grupos (`allows_multiple: false`): el producto queda con un solo grupo de este tipo; un segundo daría `422 GROUP_TYPE_SINGLE_VALUE`.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<ASIG_GRUPO2>",
  "global_product_group_id": "<GRUPO2_0689>",
  "group_type_id": "<GT_GROUP_2>",
  "status": "ACTIVE"
}
```

**Guardar:** `id` → `<ASIG_GRUPO2>`

## 7. Grupo 4 `0336` — consultar si ya existe

```http
GET /api/v1/group-types/<GT_GROUP_4>/groups?code=0336
```

**Permiso que exige la URL:** `perm:product-catalog:group-types:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:product-catalog:all:read`), `ventas.test` (por `perm:product-catalog:all:read`), `inventario.test` (por `perm:product-catalog:all:read`), `reportes.test` (por `perm:product-catalog:group-types:read`), `consulta.test` (por `perm:product-catalog:group-types:read`)

**Por qué se hace así**

- Los grupos son compartidos por muchos productos: `0336` puede existir porque otro producto (u otro ejercicio) ya lo creó. Se consulta primero para **reutilizarlo** y no intentar duplicarlo (un segundo `POST` con el mismo código responde `409 DUPLICATE_CODE`).

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [],
  "total_records": 0
}
```

**Si `items` trae el grupo:** guarde `items[0].id` → `<GRUPO4_0336>` y **salte** la llamada siguiente (crear). **Si viene vacío** (como en la respuesta de arriba, en una base nueva): haga la llamada siguiente.

## 8. Grupo 4 `0336` — crearlo (solo si la consulta vino vacía)

> **Solo si la consulta anterior devolvió `"items": []`.** Si el grupo ya existía, **omita esta llamada** y use como `<GRUPO4_0336>` el `id` que devolvió la consulta.

```http
POST /api/v1/group-types/<GT_GROUP_4>/groups
```

```json
{
  "code": "0336",
  "name": "Nestlé"
}
```

**Permiso que exige la URL:** `perm:product-catalog:group-types:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `create`
- ℹ️ Los grupos se crean dentro de su tipo de grupo: exige `create` sobre `group-types`.

**Por qué se hace así**

- `code` conserva el código del Excel (`0336`) para poder rastrear el origen del dato.
- `name` es el nombre del Excel escrito de forma legible.
- No se envía `parent_group_id`: en el Excel los grupos no tienen jerarquía.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<GRUPO4_0336>",
  "group_type_id": "<GT_GROUP_4>",
  "code": "0336",
  "name": "Nestlé",
  "status": "ACTIVE"
}
```

**Guardar:** `id` → `<GRUPO4_0336>`

## 9. Grupo 4 `0336` — asignarlo al producto

```http
POST /api/v1/products/<PRODUCTO>/group-assignments
```

```json
{
  "global_product_group_id": "<GRUPO4_0336>"
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Todo lo que se agrega **dentro** de un producto (categorías, valores, presentaciones, códigos, grupos, imágenes) exige `update` sobre `products`.

**Por qué se hace así**

- `<GRUPO4_0336>` es el `id` del grupo: el de la consulta si ya existía, o el del `POST` si se acaba de crear.
- `GROUP_4` no admite varios grupos (`allows_multiple: false`): el producto queda con un solo grupo de este tipo; un segundo daría `422 GROUP_TYPE_SINGLE_VALUE`.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<ASIG_GRUPO4>",
  "global_product_group_id": "<GRUPO4_0336>",
  "group_type_id": "<GT_GROUP_4>",
  "status": "ACTIVE"
}
```

**Guardar:** `id` → `<ASIG_GRUPO4>`

---

[← Paso anterior](10-registrar-codigos-de-barras.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](12-verificar-resultado.md)
