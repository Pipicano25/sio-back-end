# Paso 09 de 11 — Registrar los identificadores

Ejercicio 4 — Aguja hipodérmica 18G x 1½" Rymco, caja x 100 · [← Paso anterior](08-registrar-valores-y-presentaciones.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](10-crear-y-asignar-grupos.md)

**Objetivo:** EAN-13 a la unidad, GTIN-14 a la caja y referencia del fabricante como `OTHER`.

**Necesita (de pasos anteriores):** `<PRODUCTO>`, `<PRES_UNIDAD>`, `<PRES_CAJA_X100>` — pasos [06](06-crear-producto.md), [08](08-registrar-valores-y-presentaciones.md)

**Deja guardado para los siguientes pasos:** `<ID_EAN13>`, `<ID_GTIN14>`, `<ID_REF_FABRICANTE>`

---

## 1. EAN-13 `7706634002856` → unidad

```http
POST /api/v1/products/<PRODUCTO>/identifiers
```

```json
{
  "identifier_type": "EAN",
  "value": "7706634002856",
  "global_product_presentation_id": "<PRES_UNIDAD>",
  "is_primary": true
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Todo lo que se agrega **dentro** de un producto (categorías, valores, presentaciones, códigos, grupos, imágenes) exige `update` sobre `products`.

**Por qué se hace así**

- 13 dígitos con dígito de control válido → `EAN`.
- Va a la `UNIDAD` porque es el código "base" del que se deriva el GTIN-14.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<ID_EAN13>",
  "global_product_presentation_id": "<PRES_UNIDAD>",
  "identifier_type": "EAN",
  "value": "7706634002856",
  "canonical_value": "07706634002856",
  "is_primary": true
}
```

**Guardar:** `id` → `<ID_EAN13>`

## 2. GTIN-14 `27706634002850` → caja

```http
POST /api/v1/products/<PRODUCTO>/identifiers
```

```json
{
  "identifier_type": "GTIN",
  "value": "27706634002850",
  "global_product_presentation_id": "<PRES_CAJA_X100>",
  "is_primary": true
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Todo lo que se agrega **dentro** de un producto (categorías, valores, presentaciones, códigos, grupos, imágenes) exige `update` sobre `products`.

**Por qué se hace así**

- 14 dígitos → `GTIN` (el tipo `EAN` es para 8 o 13 dígitos por convención; el servicio acepta 8, 12, 13 o 14 en la familia GTIN).
- El primer dígito (`2`) es el **indicador de empaque** GS1: marca un agrupamiento del artículo `770663400285`.
- `canonical_value` es el mismo valor (ya tiene 14 dígitos) y **distinto** del canónico del EAN (`07706634002856`), por eso no chocan.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<ID_GTIN14>",
  "global_product_presentation_id": "<PRES_CAJA_X100>",
  "identifier_type": "GTIN",
  "value": "27706634002850",
  "canonical_value": "27706634002850",
  "is_primary": true
}
```

**Guardar:** `id` → `<ID_GTIN14>`

## 3. Referencia del fabricante `RFZC18B` → `OTHER`

```http
POST /api/v1/products/<PRODUCTO>/identifiers
```

```json
{
  "identifier_type": "OTHER",
  "value": "RFZC18B"
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Todo lo que se agrega **dentro** de un producto (categorías, valores, presentaciones, códigos, grupos, imágenes) exige `update` sobre `products`.

**Por qué se hace así**

- No es un código de barras: es la referencia de catálogo de Rymco. Sirve para encontrar el producto con `GET /products?identifier=RFZC18B` cuando llega en una orden de compra.
- Sin `global_product_presentation_id`: la referencia identifica al producto, no a un empaque.
- `OTHER` solo exige unicidad **dentro del producto**; otro fabricante podría usar la misma referencia.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<ID_REF_FABRICANTE>",
  "global_product_presentation_id": null,
  "identifier_type": "OTHER",
  "value": "RFZC18B",
  "canonical_value": "RFZC18B",
  "is_primary": false
}
```

**Guardar:** `id` → `<ID_REF_FABRICANTE>`

## 4. Error esperado: el mismo código como GTIN

```http
POST /api/v1/products/<PRODUCTO>/identifiers
```

```json
{
  "identifier_type": "GTIN",
  "value": "07706634002856"
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Todo lo que se agrega **dentro** de un producto (categorías, valores, presentaciones, códigos, grupos, imágenes) exige `update` sobre `products`.

**Por qué se hace así**

- `07706634002856` es el EAN-13 de la llamada 1 con un cero a la izquierda. GTIN, EAN y UPC se comparan por su forma canónica de 14 dígitos: es **el mismo código**.
- Responde `409 IDENTIFIER_COLLISION` e indica en `conflict` qué registro ya lo tiene.

**Respuesta esperada (error) — `409 Conflict`** (abreviada)

```json
{
  "status": 409,
  "code": "PRODUCT_CATALOG.IDENTIFIER_COLLISION",
  "detail": "El código 07706634002856 ya identifica otro registro del catálogo; revise la inconsistencia.",
  "conflict": {
    "global_product_id": "<PRODUCTO>",
    "global_product_presentation_id": "<PRES_UNIDAD>",
    "identifier_id": "<ID_EAN13>",
    "identifier_type": "EAN",
    "status": "ACTIVE"
  }
}
```

## 5. Error esperado: un GTIN registrado como `BARCODE`

```http
POST /api/v1/products/<PRODUCTO>/identifiers
```

```json
{
  "identifier_type": "BARCODE",
  "value": "7706634002856"
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Todo lo que se agrega **dentro** de un producto (categorías, valores, presentaciones, códigos, grupos, imágenes) exige `update` sobre `products`.

**Por qué se hace así**

- `BARCODE` es para códigos de barras **que no son GS1**. Si el valor cumple el formato GTIN/EAN/UPC, el servicio exige registrarlo con su tipo específico: `422 BARCODE_IS_GTIN`.
- El formato se valida **antes** que la unicidad: por eso responde `422` y no `409`, aunque el código ya esté registrado.
- Así no se evita la validación del dígito de control ni la detección de duplicados.

**Respuesta esperada (error) — `422 Unprocessable Content`** (abreviada)

```json
{
  "status": 422,
  "code": "PRODUCT_CATALOG.BARCODE_IS_GTIN",
  "detail": "El código cumple el estándar GTIN/EAN/UPC: regístrelo con su tipo específico."
}
```

---

> **Antes de cargar, confirme en el empaque físico** qué código está en la unidad y cuál en la caja: un identificador no se puede mover a otra presentación (solo inactivar) y su valor **no se puede volver a registrar**, aunque esté inactivo.

---

[← Paso anterior](08-registrar-valores-y-presentaciones.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](10-crear-y-asignar-grupos.md)
