# Paso 10 de 14 — Agregar la imagen del producto

Ejercicio 5 — Cepillo Colgate infantil pack x 2 (producto inactivo) · [← Paso anterior](09-codigo-interno-no-es-codigo-de-barras.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](11-crear-y-asignar-grupos.md)

**Objetivo:** Registrar un activo digital (foto).

**Necesita (de pasos anteriores):** `<PRODUCTO>` — pasos [06](06-crear-producto.md)

**Deja guardado para los siguientes pasos:** `<ACTIVO_IMAGEN>`

---

## 1. Registrar la imagen principal

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

- El Excel no trae imágenes: este paso es **ilustrativo** para mostrar cómo se registra una.
- El catálogo **no guarda el archivo**, solo la referencia (`storage_uri`). El archivo se sube antes al almacenamiento.
- `storage_uri` debe ser un URI absoluto (`s3://…`, `https://…`); si no, `422 INVALID_STORAGE_URI`.
- `is_primary: true`: es la imagen que se muestra por defecto. Hay una principal por tipo de activo.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<ACTIVO_IMAGEN>",
  "asset_type": "IMAGE",
  "file_name": "colgate-cepillo-infantil-2-5-nina-pack-x2.jpg",
  "storage_uri": "s3://sio-product-catalog/productos/colgate-cepillo-infantil-2-5-nina-pack-x2.jpg",
  "mime_type": "image/jpeg",
  "is_primary": true,
  "status": "ACTIVE"
}
```

**Guardar:** `id` → `<ACTIVO_IMAGEN>`

---

[← Paso anterior](09-codigo-interno-no-es-codigo-de-barras.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](11-crear-y-asignar-grupos.md)
