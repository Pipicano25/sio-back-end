# Paso 04 de 06 — Crear los productos globales

Ejercicio 2 — Relación comercial y precios: proveedor, cliente, productos, adopción, presentaciones y listas · [Orden del ejercicio](ORDEN.md)

---

## 1. Crear la categoría global de los productos

Paso `C-10.categoria` · usuario **`admin.test`** · ítems de la FASE 10: 6

```http
POST http://127.0.0.1:8103/api/v1/categories
```

```json
{
  "code": "MVP-<RUN_ID>",
  "name": "Categoría MVP <RUN_ID> (dato ficticio)"
}
```

**Permiso que exige la URL:** `perm:product-catalog:categories:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)

**Por qué se hace así**

- Un producto necesita una categoría vigente y una presentación activa para ser elegible para adopción.

**Respuesta esperada:** `201`

**Guardar:** `id` → `<CATEGORIA>`

**Auditoría que deja:** `CREATE_CATEGORY` (product-catalog)

## 2. Crear el producto global A

Paso `C-10.producto_a` · usuario **`admin.test`** · ítems de la FASE 10: 6

```http
POST http://127.0.0.1:8103/api/v1/products
```

```json
{
  "product_type": "GOOD",
  "canonical_name": "Producto A MVP <RUN_ID> (dato ficticio)",
  "base_unit_id": "<UNIDAD_UND>"
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)

**Respuesta esperada:** `201`

**Guardar:** `id` → `<PRODUCTO_A>`

**Auditoría que deja:** `CREATE_PRODUCT` (product-catalog)

## 3. Clasificar el producto A

Paso `C-10.categoria_a` · usuario **`admin.test`** · ítems de la FASE 10: 6

```http
POST http://127.0.0.1:8103/api/v1/products/<PRODUCTO_A>/categories
```

```json
{
  "global_category_id": "<CATEGORIA>"
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)

**Respuesta esperada:** `201`

**Guardar:** `id` → `<CATEGORIA_PRODUCTO_A>`

**Auditoría que deja:** `ADD_PRODUCT_CATEGORY` (product-catalog)

## 4. Crear la presentación base (unidad) del producto A

Paso `C-10.base_a` · usuario **`admin.test`** · ítems de la FASE 10: 7

```http
POST http://127.0.0.1:8103/api/v1/products/<PRODUCTO_A>/presentations
```

```json
{
  "code": "UND-A-<RUN_ID>",
  "name": "Unidad (dato ficticio)",
  "base_quantity": "1",
  "display_order": 1,
  "is_base": true
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)

**Respuesta esperada:** `201`

**Guardar:** `id` → `<PRESENTACION_BASE_A>`

**Auditoría que deja:** `CREATE_PRODUCT_PRESENTATION` (product-catalog)

## 5. Crear la presentación "Caja × 12" del producto A

Paso `C-10.caja_a` · usuario **`admin.test`** · ítems de la FASE 10: 7

```http
POST http://127.0.0.1:8103/api/v1/products/<PRODUCTO_A>/presentations
```

```json
{
  "code": "CJ12-A-<RUN_ID>",
  "name": "Caja x12 (dato ficticio)",
  "base_quantity": "12",
  "display_order": 2,
  "is_base": false
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)

**Por qué se hace así**

- `base_quantity = 12`: una caja equivale a 12 unidades base (compras y ventas convierten con este factor).

**Respuesta esperada:** `201`

**Guardar:** `id` → `<PRESENTACION_CAJA_A>`

**Auditoría que deja:** `CREATE_PRODUCT_PRESENTATION` (product-catalog)

## 6. Crear el producto global B

Paso `C-10.producto_b` · usuario **`admin.test`** · ítems de la FASE 10: 6

```http
POST http://127.0.0.1:8103/api/v1/products
```

```json
{
  "product_type": "GOOD",
  "canonical_name": "Producto B MVP <RUN_ID> (dato ficticio)",
  "base_unit_id": "<UNIDAD_UND>"
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)

**Respuesta esperada:** `201`

**Guardar:** `id` → `<PRODUCTO_B>`

**Auditoría que deja:** `CREATE_PRODUCT` (product-catalog)

## 7. Clasificar el producto B

Paso `C-10.categoria_b` · usuario **`admin.test`** · ítems de la FASE 10: 6

```http
POST http://127.0.0.1:8103/api/v1/products/<PRODUCTO_B>/categories
```

```json
{
  "global_category_id": "<CATEGORIA>"
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)

**Respuesta esperada:** `201`

**Guardar:** `id` → `<CATEGORIA_PRODUCTO_B>`

**Auditoría que deja:** `ADD_PRODUCT_CATEGORY` (product-catalog)

## 8. Crear la presentación base (unidad) del producto B

Paso `C-10.base_b` · usuario **`admin.test`** · ítems de la FASE 10: 7

```http
POST http://127.0.0.1:8103/api/v1/products/<PRODUCTO_B>/presentations
```

```json
{
  "code": "UND-B-<RUN_ID>",
  "name": "Unidad (dato ficticio)",
  "base_quantity": "1",
  "display_order": 1,
  "is_base": true
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)

**Respuesta esperada:** `201`

**Guardar:** `id` → `<PRESENTACION_BASE_B>`

**Auditoría que deja:** `CREATE_PRODUCT_PRESENTATION` (product-catalog)
