# Paso 13 de 13 — Verificar el comportamiento del producto inactivo

Ejercicio 5 — Cepillo Colgate infantil pack x 2 (producto inactivo) · [← Paso anterior](12-inactivar-producto.md) · [Orden del ejercicio](ORDEN.md)

**Objetivo:** Ver qué se puede y qué no se puede hacer con un producto inactivo.

**Necesita (de pasos anteriores):** `<PRODUCTO>` — pasos [06](06-crear-producto.md)

---

## 1. Error esperado: agregar una presentación

```http
POST /api/v1/products/<PRODUCTO>/presentations
```

```json
{
  "code": "UNIDAD",
  "name": "Cepillo individual",
  "base_quantity": 1,
  "is_base": true
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Todo lo que se agrega **dentro** de un producto (categorías, valores, presentaciones, códigos, grupos, imágenes) exige `update` sobre `products`.

**Por qué se hace así**

- Sobre un producto inactivo solo se consultan o inactivan sus elementos: `422 PRODUCT_INACTIVE`.

**Respuesta esperada (error) — `422 Unprocessable Content`** (abreviada)

```json
{
  "status": 422,
  "code": "PRODUCT_CATALOG.PRODUCT_INACTIVE",
  "detail": "El producto está inactivo: sus elementos solo pueden consultarse o inactivarse."
}
```

## 2. Buscar productos inactivos

```http
GET /api/v1/products?status=INACTIVE&search=cepillo
```

**Permiso que exige la URL:** `perm:product-catalog:products:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:product-catalog:all:read`), `ventas.test` (por `perm:product-catalog:all:read`), `inventario.test` (por `perm:product-catalog:all:read`), `reportes.test` (por `perm:all:all:read`), `consulta.test` (por `perm:all:all:read`)

**Por qué se hace así**

- Los inactivos se siguen consultando: el filtro `status` los separa de los activos.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "canonical_name": "Colgate cepillo dental infantil 2 a 5 años extra suave niña",
      "status": "INACTIVE"
    }
  ],
  "total_records": 1
}
```

## 3. Consultar el detalle

```http
GET /api/v1/products/<PRODUCTO>?expand=detail
```

**Permiso que exige la URL:** `perm:product-catalog:products:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:product-catalog:all:read`), `ventas.test` (por `perm:product-catalog:all:read`), `inventario.test` (por `perm:product-catalog:all:read`), `reportes.test` (por `perm:all:all:read`), `consulta.test` (por `perm:all:all:read`)

**Por qué se hace así**

- Toda la información se conserva. Si se reactiva (`POST /products/{id}/reactivate` con la `version` actual), vuelve a ser elegible sin recargar nada.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "status": "INACTIVE",
  "eligible_for_adoption": false,
  "detail": {
    "presentations": [
      {
        "code": "PACK_X2",
        "status": "ACTIVE"
      }
    ],
    "assets": [
      {
        "file_name": "colgate-cepillo-infantil-2-5-nina-pack-x2.jpg"
      }
    ],
    "identifiers": []
  }
}
```

---

[← Paso anterior](12-inactivar-producto.md) · [Orden del ejercicio](ORDEN.md)
