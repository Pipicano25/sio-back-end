# Paso 10 de 14 — Agregar la imagen de la presentación

Ejercicio 5 — Cepillo Colgate infantil pack x 2 (producto inactivo) · [← Paso anterior](09-codigo-interno-no-es-codigo-de-barras.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](11-crear-y-asignar-grupos.md)

**Objetivo:** Cargar la foto del pack x 2 y dejarla como imagen principal de esa presentación (spec 024).

**Necesita (de pasos anteriores):** `<PRODUCTO>`, `<PRES_PACK_X2>` — pasos [06](06-crear-producto.md), [08](08-crear-presentacion.md)

**Deja guardado para los siguientes pasos:** `<ACTIVO_IMAGEN>`, `<ACTIVO_IMAGEN_2>`, `<VERSION_IMAGEN_2>`

---

## 1. Cargar la imagen de la presentación

```http
POST /api/v1/products/<PRODUCTO>/presentations/<PRES_PACK_X2>/assets/upload
```

Cuerpo `multipart/form-data` con **un solo campo**, `file`, que contiene el archivo de la imagen. Con cURL:

```bash
curl -X POST "http://localhost:8003/api/v1/products/<PRODUCTO>/presentations/<PRES_PACK_X2>/assets/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@colgate-cepillo-infantil-2-5-nina-pack-x2.png"
```

**Permiso que exige la URL:** `perm:product-catalog:products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Todo lo que se agrega **dentro** de un producto (categorías, valores, presentaciones, códigos, grupos, imágenes) exige `update` sobre `products`.

**Por qué se hace así**

- El Excel no trae imágenes: la foto de este paso es **ficticia** (un PNG generado) y solo muestra cómo se carga una.
- Las imágenes pertenecen a una **presentación**, no al producto: cada presentación puede tener su propia foto. Esta es la del pack x 2.
- Se envía el archivo (`multipart/form-data`, campo `file`). El catálogo lo guarda en el almacenamiento de SIO y responde sin exponer bucket ni clave: `content_url` (con token) e `image_url` (URL pública firmada, o `null` si está deshabilitada).
- La última imagen cargada queda **principal** automáticamente.
- El tipo se toma del **contenido** (JPEG, PNG o WebP); la extensión y el tipo declarado se ignoran.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<ACTIVO_IMAGEN>",
  "global_product_presentation_id": "<PRES_PACK_X2>",
  "asset_type": "IMAGE",
  "file_name": "colgate-cepillo-infantil-2-5-nina-pack-x2.png",
  "mime_type": "image/png",
  "is_primary": true,
  "status": "ACTIVE",
  "content_url": "/api/v1/products/<PRODUCTO>/presentations/<PRES_PACK_X2>/assets/<ACTIVO_IMAGEN>/content"
}
```

**Guardar:** `id` → `<ACTIVO_IMAGEN>`

## 2. Error esperado: cargar otra vez el mismo archivo

```http
POST /api/v1/products/<PRODUCTO>/presentations/<PRES_PACK_X2>/assets/upload
```

Cuerpo `multipart/form-data` con **un solo campo**, `file`, que contiene el archivo de la imagen. Con cURL:

```bash
curl -X POST "http://localhost:8003/api/v1/products/<PRODUCTO>/presentations/<PRES_PACK_X2>/assets/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@copia-del-mismo-archivo.png"
```

**Permiso que exige la URL:** `perm:product-catalog:products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Todo lo que se agrega **dentro** de un producto (categorías, valores, presentaciones, códigos, grupos, imágenes) exige `update` sobre `products`.

**Por qué se hace así**

- El catálogo compara el **contenido** (SHA-256), no el nombre: la presentación ya tiene esa imagen. `existing_asset_id` dice cuál es; no se crea otra ni se vuelve a guardar el archivo.

**Respuesta esperada (error) — `409 Conflict`** (abreviada)

```json
{
  "status": 409,
  "code": "PRODUCT_CATALOG.DUPLICATE_ASSET_CONTENT",
  "existing_asset_id": "<ACTIVO_IMAGEN>"
}
```

## 3. Cargar una segunda imagen (foto lateral)

```http
POST /api/v1/products/<PRODUCTO>/presentations/<PRES_PACK_X2>/assets/upload
```

Cuerpo `multipart/form-data` con **un solo campo**, `file`, que contiene el archivo de la imagen. Con cURL:

```bash
curl -X POST "http://localhost:8003/api/v1/products/<PRODUCTO>/presentations/<PRES_PACK_X2>/assets/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@colgate-cepillo-infantil-pack-x2-lateral.png"
```

**Permiso que exige la URL:** `perm:product-catalog:products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Todo lo que se agrega **dentro** de un producto (categorías, valores, presentaciones, códigos, grupos, imágenes) exige `update` sobre `products`.

**Por qué se hace así**

- Una presentación puede tener varias imágenes. La recién cargada pasa a ser la principal; la anterior sigue `ACTIVE` como secundaria.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<ACTIVO_IMAGEN_2>",
  "file_name": "colgate-cepillo-infantil-pack-x2-lateral.png",
  "is_primary": true,
  "status": "ACTIVE"
}
```

**Guardar:** `id` → `<ACTIVO_IMAGEN_2>` · `version` → `<VERSION_IMAGEN_2>`

## 4. Listar las imágenes de la presentación

```http
GET /api/v1/products/<PRODUCTO>/presentations/<PRES_PACK_X2>/assets
```

**Permiso que exige la URL:** `perm:product-catalog:products:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:product-catalog:all:read`), `ventas.test` (por `perm:product-catalog:all:read`), `inventario.test` (por `perm:product-catalog:all:read`), `reportes.test` (por `perm:product-catalog:products:read`), `consulta.test` (por `perm:product-catalog:products:read`)

**Por qué se hace así**

- Solo las `ACTIVE`, la principal primero. Para ver las eliminadas: `?status=INACTIVE`.

**Respuesta esperada — `200 OK`** (abreviada)

```json
[
  {
    "id": "<ACTIVO_IMAGEN_2>",
    "file_name": "colgate-cepillo-infantil-pack-x2-lateral.png",
    "is_primary": true,
    "status": "ACTIVE"
  },
  {
    "id": "<ACTIVO_IMAGEN>",
    "file_name": "colgate-cepillo-infantil-2-5-nina-pack-x2.png",
    "is_primary": false,
    "status": "ACTIVE"
  }
]
```

## 5. Eliminar la segunda imagen

```http
POST /api/v1/products/<PRODUCTO>/presentations/<PRES_PACK_X2>/assets/<ACTIVO_IMAGEN_2>/deactivate
```

```json
{
  "version": "<VERSION_IMAGEN_2>"
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:deactivate`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`)
- ❌ **No pueden (responde `403`):** `supervisor.test` — sobre `product-catalog` solo tiene `create`, `read`, `update`; le falta `deactivate`; `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `deactivate`
- ℹ️ Inactivar es una acción propia (`deactivate`): no la cubren `create` ni `update`.

**Por qué se hace así**

- La eliminación es lógica: la imagen queda `INACTIVE` y el archivo **no** se borra del almacenamiento.
- Era la principal, así que la imagen `ACTIVE` más reciente (la foto del frente) vuelve a serlo automáticamente.
- Exige `perm:product-catalog:products:deactivate`.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "id": "<ACTIVO_IMAGEN_2>",
  "is_primary": false,
  "status": "INACTIVE",
  "version": 3
}
```

**Guardar:** `version` → `<VERSION_IMAGEN_2>`

## 6. Reactivar la segunda imagen

```http
POST /api/v1/products/<PRODUCTO>/presentations/<PRES_PACK_X2>/assets/<ACTIVO_IMAGEN_2>/reactivate
```

```json
{
  "version": "<VERSION_IMAGEN_2>"
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:deactivate`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`)
- ❌ **No pueden (responde `403`):** `supervisor.test` — sobre `product-catalog` solo tiene `create`, `read`, `update`; le falta `deactivate`; `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `deactivate`
- ℹ️ Inactivar es una acción propia (`deactivate`): no la cubren `create` ni `update`.

**Por qué se hace así**

- Vuelve a `ACTIVE`, pero **no** se marca como principal: la principal sigue siendo la del frente.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "id": "<ACTIVO_IMAGEN_2>",
  "is_primary": false,
  "status": "ACTIVE",
  "version": 4
}
```

**Guardar:** `version` → `<VERSION_IMAGEN_2>`

## 7. Marcar la segunda imagen como principal

```http
POST /api/v1/products/<PRODUCTO>/presentations/<PRES_PACK_X2>/assets/<ACTIVO_IMAGEN_2>/set-primary
```

```json
{
  "version": "<VERSION_IMAGEN_2>"
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Todo lo que se agrega **dentro** de un producto (categorías, valores, presentaciones, códigos, grupos, imágenes) exige `update` sobre `products`.

**Por qué se hace así**

- La principal anterior deja de serlo en la misma operación: nunca hay dos.
- El contenido de cada imagen se descarga con su `content_url` (con token) o se muestra con `image_url` en `<img src>`.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "id": "<ACTIVO_IMAGEN_2>",
  "is_primary": true,
  "status": "ACTIVE",
  "version": 5
}
```

## 8. Error esperado: registrar la imagen en el producto

```http
POST /api/v1/products/<PRODUCTO>/assets
```

```json
{
  "asset_type": "IMAGE",
  "file_name": "colgate-cepillo-infantil-2-5-nina-pack-x2.jpg",
  "storage_uri": "s3://sio-product-catalog/productos/colgate-cepillo-infantil-2-5-nina-pack-x2.jpg",
  "mime_type": "image/jpeg",
  "is_primary": true
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Todo lo que se agrega **dentro** de un producto (categorías, valores, presentaciones, códigos, grupos, imágenes) exige `update` sobre `products`.

**Por qué se hace así**

- Los productos no tienen imágenes directas: `422 IMAGE_REQUIRES_PRESENTATION`. Las fichas técnicas, manuales y certificados sí se siguen registrando en el producto.

**Respuesta esperada (error) — `422 Unprocessable Content`** (abreviada)

```json
{
  "status": 422,
  "code": "PRODUCT_CATALOG.IMAGE_REQUIRES_PRESENTATION",
  "detail": "Las imágenes pertenecen a una presentación: use /products/{product_id}/presentations/{presentation_id}/assets."
}
```

---

[← Paso anterior](09-codigo-interno-no-es-codigo-de-barras.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](11-crear-y-asignar-grupos.md)
