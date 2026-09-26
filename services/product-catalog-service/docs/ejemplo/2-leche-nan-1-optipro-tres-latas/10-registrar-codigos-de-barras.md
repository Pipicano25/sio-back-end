# Paso 10 de 12 — Registrar los códigos de barras

Ejercicio 2 — Leche NAN 1 Optipro: tres filas del Excel, un solo producto · [← Paso anterior](09-crear-presentaciones.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](11-crear-y-asignar-grupos.md)

**Objetivo:** Cada EAN del Excel va a la presentación de su fila.

**Necesita (de pasos anteriores):** `<PRODUCTO>`, `<PRES_LATA_400G>`, `<PRES_LATA_900G>`, `<PRES_LATA_1100G>` — pasos [06](06-crear-producto.md), [09](09-crear-presentaciones.md)

**Deja guardado para los siguientes pasos:** `<ID_EAN_400G>`, `<ID_EAN_900G>`, `<ID_EAN_1100G>`

---

## 1. EAN `7501059227453` → lata 400 g

```http
POST /api/v1/products/<PRODUCTO>/identifiers
```

```json
{
  "identifier_type": "EAN",
  "value": "7501059227453",
  "global_product_presentation_id": "<PRES_LATA_400G>",
  "is_primary": true
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Todo lo que se agrega **dentro** de un producto (categorías, valores, presentaciones, códigos, grupos, imágenes) exige `update` sobre `products`.

**Por qué se hace así**

- Cada tamaño tiene su propio código: al escanear se debe saber qué lata se vendió.
- `is_primary: true`: la marca de principal es **por presentación**, así que cada lata tiene el suyo.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<ID_EAN_400G>",
  "global_product_presentation_id": "<PRES_LATA_400G>",
  "identifier_type": "EAN",
  "value": "7501059227453",
  "is_primary": true
}
```

**Guardar:** `id` → `<ID_EAN_400G>`

## 2. EAN `7501059227644` → lata 900 g

```http
POST /api/v1/products/<PRODUCTO>/identifiers
```

```json
{
  "identifier_type": "EAN",
  "value": "7501059227644",
  "global_product_presentation_id": "<PRES_LATA_900G>",
  "is_primary": true
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Todo lo que se agrega **dentro** de un producto (categorías, valores, presentaciones, códigos, grupos, imágenes) exige `update` sobre `products`.

**Por qué se hace así**

- Código de la fila 6138.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<ID_EAN_900G>",
  "global_product_presentation_id": "<PRES_LATA_900G>",
  "value": "7501059227644",
  "is_primary": true
}
```

**Guardar:** `id` → `<ID_EAN_900G>`

## 3. EAN `7501059279124` → lata 1100 g

```http
POST /api/v1/products/<PRODUCTO>/identifiers
```

```json
{
  "identifier_type": "EAN",
  "value": "7501059279124",
  "global_product_presentation_id": "<PRES_LATA_1100G>",
  "is_primary": true
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Todo lo que se agrega **dentro** de un producto (categorías, valores, presentaciones, códigos, grupos, imágenes) exige `update` sobre `products`.

**Por qué se hace así**

- Código de la fila 7333.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<ID_EAN_1100G>",
  "global_product_presentation_id": "<PRES_LATA_1100G>",
  "value": "7501059279124",
  "is_primary": true
}
```

**Guardar:** `id` → `<ID_EAN_1100G>`

---

[← Paso anterior](09-crear-presentaciones.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](11-crear-y-asignar-grupos.md)
