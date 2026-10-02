# Paso 12 de 13 — Crear y asignar los grupos

Ejercicio 1 — Acetaminofén Adorem 500 mg, caja x 100 · [← Paso anterior](11-registrar-codigos-de-barras.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](13-verificar-resultado.md)

**Objetivo:** Conservar la agrupación del sistema anterior (`Grupo 1` a `Grupo 4`).

**Necesita (de pasos anteriores):** `<GT_GROUP_1>`, `<PRODUCTO>`, `<GT_GROUP_2>`, `<GT_GROUP_3>`, `<GT_GROUP_4>` — pasos [01](01-consultar-datos-base.md), [07](07-crear-producto.md)

**Deja guardado para los siguientes pasos:** `<GRUPO1_0001>`, `<ASIG_GRUPO1>`, `<GRUPO2_0012>`, `<ASIG_GRUPO2>`, `<GRUPO3_0085>`, `<ASIG_GRUPO3>`, `<GRUPO4_0170>`, `<ASIG_GRUPO4>`

Por cada grupo se hacen tres llamadas: **consultar** si existe, **crearlo** solo si no existe y **asignarlo** al producto. `Grupo 5 = 0695 NO APLICA` **no** se importa: no agrupa nada.

---

## 1. Grupo 1 `0001` — consultar si ya existe

```http
GET /api/v1/group-types/<GT_GROUP_1>/groups?code=0001
```

**Permiso que exige la URL:** `perm:product-catalog:group-types:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:product-catalog:all:read`), `ventas.test` (por `perm:product-catalog:all:read`), `inventario.test` (por `perm:product-catalog:all:read`), `reportes.test` (por `perm:product-catalog:group-types:read`), `consulta.test` (por `perm:product-catalog:group-types:read`)

**Por qué se hace así**

- Los grupos son compartidos por muchos productos: `0001` puede existir porque otro producto (u otro ejercicio) ya lo creó. Se consulta primero para **reutilizarlo** y no intentar duplicarlo (un segundo `POST` con el mismo código responde `409 DUPLICATE_CODE`).

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [],
  "total_records": 0
}
```

**Si `items` trae el grupo:** guarde `items[0].id` → `<GRUPO1_0001>` y **salte** la llamada siguiente (crear). **Si viene vacío** (como en la respuesta de arriba, en una base nueva): haga la llamada siguiente.

## 2. Grupo 1 `0001` — crearlo (solo si la consulta vino vacía)

> **Solo si la consulta anterior devolvió `"items": []`.** Si el grupo ya existía, **omita esta llamada** y use como `<GRUPO1_0001>` el `id` que devolvió la consulta.

```http
POST /api/v1/group-types/<GT_GROUP_1>/groups
```

```json
{
  "code": "0001",
  "name": "Medicamentos éticos"
}
```

**Permiso que exige la URL:** `perm:product-catalog:group-types:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `create`
- ℹ️ Los grupos se crean dentro de su tipo de grupo: exige `create` sobre `group-types`.

**Por qué se hace así**

- `code` conserva el código del Excel (`0001`) para poder rastrear el origen del dato.
- `name` es el nombre del Excel escrito de forma legible.
- No se envía `parent_group_id`: en el Excel los grupos no tienen jerarquía.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<GRUPO1_0001>",
  "group_type_id": "<GT_GROUP_1>",
  "code": "0001",
  "name": "Medicamentos éticos",
  "status": "ACTIVE"
}
```

**Guardar:** `id` → `<GRUPO1_0001>`

## 3. Grupo 1 `0001` — asignarlo al producto

```http
POST /api/v1/products/<PRODUCTO>/group-assignments
```

```json
{
  "global_product_group_id": "<GRUPO1_0001>"
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Todo lo que se agrega **dentro** de un producto (categorías, valores, presentaciones, códigos, grupos, imágenes) exige `update` sobre `products`.

**Por qué se hace así**

- `<GRUPO1_0001>` es el `id` del grupo: el de la consulta si ya existía, o el del `POST` si se acaba de crear.
- `GROUP_1` no admite varios grupos (`allows_multiple: false`): el producto queda con un solo grupo de este tipo; un segundo daría `422 GROUP_TYPE_SINGLE_VALUE`.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<ASIG_GRUPO1>",
  "global_product_group_id": "<GRUPO1_0001>",
  "group_type_id": "<GT_GROUP_1>",
  "status": "ACTIVE"
}
```

**Guardar:** `id` → `<ASIG_GRUPO1>`

## 4. Grupo 2 `0012` — consultar si ya existe

```http
GET /api/v1/group-types/<GT_GROUP_2>/groups?code=0012
```

**Permiso que exige la URL:** `perm:product-catalog:group-types:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:product-catalog:all:read`), `ventas.test` (por `perm:product-catalog:all:read`), `inventario.test` (por `perm:product-catalog:all:read`), `reportes.test` (por `perm:product-catalog:group-types:read`), `consulta.test` (por `perm:product-catalog:group-types:read`)

**Por qué se hace así**

- Los grupos son compartidos por muchos productos: `0012` puede existir porque otro producto (u otro ejercicio) ya lo creó. Se consulta primero para **reutilizarlo** y no intentar duplicarlo (un segundo `POST` con el mismo código responde `409 DUPLICATE_CODE`).

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [],
  "total_records": 0
}
```

**Si `items` trae el grupo:** guarde `items[0].id` → `<GRUPO2_0012>` y **salte** la llamada siguiente (crear). **Si viene vacío** (como en la respuesta de arriba, en una base nueva): haga la llamada siguiente.

## 5. Grupo 2 `0012` — crearlo (solo si la consulta vino vacía)

> **Solo si la consulta anterior devolvió `"items": []`.** Si el grupo ya existía, **omita esta llamada** y use como `<GRUPO2_0012>` el `id` que devolvió la consulta.

```http
POST /api/v1/group-types/<GT_GROUP_2>/groups
```

```json
{
  "code": "0012",
  "name": "OTC"
}
```

**Permiso que exige la URL:** `perm:product-catalog:group-types:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `create`
- ℹ️ Los grupos se crean dentro de su tipo de grupo: exige `create` sobre `group-types`.

**Por qué se hace así**

- `code` conserva el código del Excel (`0012`) para poder rastrear el origen del dato.
- `name` es el nombre del Excel escrito de forma legible.
- No se envía `parent_group_id`: en el Excel los grupos no tienen jerarquía.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<GRUPO2_0012>",
  "group_type_id": "<GT_GROUP_2>",
  "code": "0012",
  "name": "OTC",
  "status": "ACTIVE"
}
```

**Guardar:** `id` → `<GRUPO2_0012>`

## 6. Grupo 2 `0012` — asignarlo al producto

```http
POST /api/v1/products/<PRODUCTO>/group-assignments
```

```json
{
  "global_product_group_id": "<GRUPO2_0012>"
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Todo lo que se agrega **dentro** de un producto (categorías, valores, presentaciones, códigos, grupos, imágenes) exige `update` sobre `products`.

**Por qué se hace así**

- `<GRUPO2_0012>` es el `id` del grupo: el de la consulta si ya existía, o el del `POST` si se acaba de crear.
- `GROUP_2` no admite varios grupos (`allows_multiple: false`): el producto queda con un solo grupo de este tipo; un segundo daría `422 GROUP_TYPE_SINGLE_VALUE`.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<ASIG_GRUPO2>",
  "global_product_group_id": "<GRUPO2_0012>",
  "group_type_id": "<GT_GROUP_2>",
  "status": "ACTIVE"
}
```

**Guardar:** `id` → `<ASIG_GRUPO2>`

## 7. Grupo 3 `0085` — consultar si ya existe

```http
GET /api/v1/group-types/<GT_GROUP_3>/groups?code=0085
```

**Permiso que exige la URL:** `perm:product-catalog:group-types:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:product-catalog:all:read`), `ventas.test` (por `perm:product-catalog:all:read`), `inventario.test` (por `perm:product-catalog:all:read`), `reportes.test` (por `perm:product-catalog:group-types:read`), `consulta.test` (por `perm:product-catalog:group-types:read`)

**Por qué se hace así**

- Los grupos son compartidos por muchos productos: `0085` puede existir porque otro producto (u otro ejercicio) ya lo creó. Se consulta primero para **reutilizarlo** y no intentar duplicarlo (un segundo `POST` con el mismo código responde `409 DUPLICATE_CODE`).

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [],
  "total_records": 0
}
```

**Si `items` trae el grupo:** guarde `items[0].id` → `<GRUPO3_0085>` y **salte** la llamada siguiente (crear). **Si viene vacío** (como en la respuesta de arriba, en una base nueva): haga la llamada siguiente.

## 8. Grupo 3 `0085` — crearlo (solo si la consulta vino vacía)

> **Solo si la consulta anterior devolvió `"items": []`.** Si el grupo ya existía, **omita esta llamada** y use como `<GRUPO3_0085>` el `id` que devolvió la consulta.

```http
POST /api/v1/group-types/<GT_GROUP_3>/groups
```

```json
{
  "code": "0085",
  "name": "Analgésicos"
}
```

**Permiso que exige la URL:** `perm:product-catalog:group-types:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `create`
- ℹ️ Los grupos se crean dentro de su tipo de grupo: exige `create` sobre `group-types`.

**Por qué se hace así**

- `code` conserva el código del Excel (`0085`) para poder rastrear el origen del dato.
- `name` es el nombre del Excel escrito de forma legible.
- No se envía `parent_group_id`: en el Excel los grupos no tienen jerarquía.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<GRUPO3_0085>",
  "group_type_id": "<GT_GROUP_3>",
  "code": "0085",
  "name": "Analgésicos",
  "status": "ACTIVE"
}
```

**Guardar:** `id` → `<GRUPO3_0085>`

## 9. Grupo 3 `0085` — asignarlo al producto

```http
POST /api/v1/products/<PRODUCTO>/group-assignments
```

```json
{
  "global_product_group_id": "<GRUPO3_0085>"
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Todo lo que se agrega **dentro** de un producto (categorías, valores, presentaciones, códigos, grupos, imágenes) exige `update` sobre `products`.

**Por qué se hace así**

- `<GRUPO3_0085>` es el `id` del grupo: el de la consulta si ya existía, o el del `POST` si se acaba de crear.
- `GROUP_3` no admite varios grupos (`allows_multiple: false`): el producto queda con un solo grupo de este tipo; un segundo daría `422 GROUP_TYPE_SINGLE_VALUE`.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<ASIG_GRUPO3>",
  "global_product_group_id": "<GRUPO3_0085>",
  "group_type_id": "<GT_GROUP_3>",
  "status": "ACTIVE"
}
```

**Guardar:** `id` → `<ASIG_GRUPO3>`

## 10. Grupo 4 `0170` — consultar si ya existe

```http
GET /api/v1/group-types/<GT_GROUP_4>/groups?code=0170
```

**Permiso que exige la URL:** `perm:product-catalog:group-types:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:product-catalog:all:read`), `ventas.test` (por `perm:product-catalog:all:read`), `inventario.test` (por `perm:product-catalog:all:read`), `reportes.test` (por `perm:product-catalog:group-types:read`), `consulta.test` (por `perm:product-catalog:group-types:read`)

**Por qué se hace así**

- Los grupos son compartidos por muchos productos: `0170` puede existir porque otro producto (u otro ejercicio) ya lo creó. Se consulta primero para **reutilizarlo** y no intentar duplicarlo (un segundo `POST` con el mismo código responde `409 DUPLICATE_CODE`).

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [],
  "total_records": 0
}
```

**Si `items` trae el grupo:** guarde `items[0].id` → `<GRUPO4_0170>` y **salte** la llamada siguiente (crear). **Si viene vacío** (como en la respuesta de arriba, en una base nueva): haga la llamada siguiente.

## 11. Grupo 4 `0170` — crearlo (solo si la consulta vino vacía)

> **Solo si la consulta anterior devolvió `"items": []`.** Si el grupo ya existía, **omita esta llamada** y use como `<GRUPO4_0170>` el `id` que devolvió la consulta.

```http
POST /api/v1/group-types/<GT_GROUP_4>/groups
```

```json
{
  "code": "0170",
  "name": "Siegfried"
}
```

**Permiso que exige la URL:** `perm:product-catalog:group-types:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `create`
- ℹ️ Los grupos se crean dentro de su tipo de grupo: exige `create` sobre `group-types`.

**Por qué se hace así**

- `code` conserva el código del Excel (`0170`) para poder rastrear el origen del dato.
- `name` es el nombre del Excel escrito de forma legible.
- No se envía `parent_group_id`: en el Excel los grupos no tienen jerarquía.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<GRUPO4_0170>",
  "group_type_id": "<GT_GROUP_4>",
  "code": "0170",
  "name": "Siegfried",
  "status": "ACTIVE"
}
```

**Guardar:** `id` → `<GRUPO4_0170>`

## 12. Grupo 4 `0170` — asignarlo al producto

```http
POST /api/v1/products/<PRODUCTO>/group-assignments
```

```json
{
  "global_product_group_id": "<GRUPO4_0170>"
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Todo lo que se agrega **dentro** de un producto (categorías, valores, presentaciones, códigos, grupos, imágenes) exige `update` sobre `products`.

**Por qué se hace así**

- `<GRUPO4_0170>` es el `id` del grupo: el de la consulta si ya existía, o el del `POST` si se acaba de crear.
- `GROUP_4` no admite varios grupos (`allows_multiple: false`): el producto queda con un solo grupo de este tipo; un segundo daría `422 GROUP_TYPE_SINGLE_VALUE`.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<ASIG_GRUPO4>",
  "global_product_group_id": "<GRUPO4_0170>",
  "group_type_id": "<GT_GROUP_4>",
  "status": "ACTIVE"
}
```

**Guardar:** `id` → `<ASIG_GRUPO4>`

---

[← Paso anterior](11-registrar-codigos-de-barras.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](13-verificar-resultado.md)
