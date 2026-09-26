# Paso 08 de 11 — Registrar atributos y presentaciones

Ejercicio 4 — Aguja hipodérmica 18G x 1½" Rymco, caja x 100 · [← Paso anterior](07-clasificar-producto.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](09-registrar-identificadores.md)

**Objetivo:** Calibre 18, longitud 1.5 pulgadas; presentaciones unidad y caja x 100.

**Necesita (de pasos anteriores):** `<PRODUCTO>`, `<ATR_CALIBRE_AGUJA>`, `<ATR_LONGITUD_AGUJA>`, `<BOX>` — pasos [01](01-consultar-datos-base.md), [04](04-crear-atributos.md), [06](06-crear-producto.md)

**Deja guardado para los siguientes pasos:** `<PRES_UNIDAD>`, `<PRES_CAJA_X100>`

---

## 1. Calibre = 18

```http
PUT /api/v1/products/<PRODUCTO>/attribute-values/<ATR_CALIBRE_AGUJA>
```

```json
{
  "integer_value": 18
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Todo lo que se agrega **dentro** de un producto (categorías, valores, presentaciones, códigos, grupos, imágenes) exige `update` sobre `products`.

**Por qué se hace así**

- `INTEGER` → `integer_value`.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "attribute_definition_id": "<ATR_CALIBRE_AGUJA>",
  "integer_value": 18
}
```

## 2. Longitud = 1.5 pulgadas

```http
PUT /api/v1/products/<PRODUCTO>/attribute-values/<ATR_LONGITUD_AGUJA>
```

```json
{
  "decimal_value": 1.5
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Todo lo que se agrega **dentro** de un producto (categorías, valores, presentaciones, códigos, grupos, imágenes) exige `update` sobre `products`.

**Por qué se hace así**

- `1 1/2` del Excel → `1.5`. Se admiten hasta 8 decimales.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "attribute_definition_id": "<ATR_LONGITUD_AGUJA>",
  "decimal_value": "1.50000000"
}
```

## 3. Presentación base `UNIDAD`

```http
POST /api/v1/products/<PRODUCTO>/presentations
```

```json
{
  "code": "UNIDAD",
  "name": "Aguja individual",
  "base_quantity": 1,
  "display_order": 1,
  "is_base": true
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Todo lo que se agrega **dentro** de un producto (categorías, valores, presentaciones, códigos, grupos, imágenes) exige `update` sobre `products`.

**Por qué se hace así**

- Cada aguja viene en su empaque estéril individual y se vende suelta en farmacias.
- El EAN-13 identifica este nivel (ver paso 9). `base_quantity: 1` por ser base.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<PRES_UNIDAD>",
  "code": "UNIDAD",
  "base_quantity": "1.00000000",
  "is_base": true
}
```

**Guardar:** `id` → `<PRES_UNIDAD>`

## 4. Presentación `CAJA_X100`

```http
POST /api/v1/products/<PRODUCTO>/presentations
```

```json
{
  "code": "CAJA_X100",
  "name": "Caja x 100 agujas",
  "packaging_type_id": "<BOX>",
  "base_quantity": 100,
  "display_order": 2,
  "is_base": false
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Todo lo que se agrega **dentro** de un producto (categorías, valores, presentaciones, códigos, grupos, imágenes) exige `update` sobre `products`.

**Por qué se hace así**

- Factor 100 (`Contenido Interno = 100`).

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<PRES_CAJA_X100>",
  "code": "CAJA_X100",
  "packaging_type_id": "<BOX>",
  "base_quantity": "100.00000000",
  "is_base": false
}
```

**Guardar:** `id` → `<PRES_CAJA_X100>`

---

[← Paso anterior](07-clasificar-producto.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](09-registrar-identificadores.md)
