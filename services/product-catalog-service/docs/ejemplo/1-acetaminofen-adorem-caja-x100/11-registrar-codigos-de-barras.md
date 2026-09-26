# Paso 11 de 13 — Registrar los códigos de barras

Ejercicio 1 — Acetaminofén Adorem 500 mg, caja x 100 · [← Paso anterior](10-crear-presentaciones.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](12-crear-y-asignar-grupos.md)

**Objetivo:** Asociar los dos EAN del Excel a la caja.

**Necesita (de pasos anteriores):** `<PRODUCTO>`, `<PRES_CAJA_X100>` — pasos [07](07-crear-producto.md), [10](10-crear-presentaciones.md)

**Deja guardado para los siguientes pasos:** `<ID_EAN_1>`, `<ID_EAN_2>`

---

## 1. EAN `7707355056876` (principal de la caja)

```http
POST /api/v1/products/<PRODUCTO>/identifiers
```

```json
{
  "identifier_type": "EAN",
  "value": "7707355056876",
  "global_product_presentation_id": "<PRES_CAJA_X100>",
  "is_primary": true
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Todo lo que se agrega **dentro** de un producto (categorías, valores, presentaciones, códigos, grupos, imágenes) exige `update` sobre `products`.

**Por qué se hace así**

- `EAN` porque son 13 dígitos con dígito de control GS1 válido (el servicio lo verifica: si no, `422 INVALID_CHECK_DIGIT`).
- `global_product_presentation_id` lo liga a la **caja**: al escanearlo se sabe que se vendió una caja de 100, no una tableta.
- `is_primary: true`: es el código que se mostrará por defecto para la caja.
- El valor se envía como **texto**, nunca como número: así no se pierden ceros a la izquierda.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<ID_EAN_1>",
  "global_product_presentation_id": "<PRES_CAJA_X100>",
  "identifier_type": "EAN",
  "value": "7707355056876",
  "canonical_value": "07707355056876",
  "is_primary": true
}
```

**Guardar:** `id` → `<ID_EAN_1>`

## 2. EAN `7707355052038` (segundo código de la caja)

```http
POST /api/v1/products/<PRODUCTO>/identifiers
```

```json
{
  "identifier_type": "EAN",
  "value": "7707355052038",
  "global_product_presentation_id": "<PRES_CAJA_X100>",
  "is_primary": false
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Todo lo que se agrega **dentro** de un producto (categorías, valores, presentaciones, códigos, grupos, imágenes) exige `update` sobre `products`.

**Por qué se hace así**

- Una misma presentación puede tener varios códigos (por ejemplo, empaque antiguo y nuevo). Los dos deben leerse en caja.
- `is_primary: false` porque la caja ya tiene un principal.
- `canonical_value` completa a 14 dígitos: con él el catálogo detecta el mismo código aunque se registre como GTIN, EAN o UPC.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<ID_EAN_2>",
  "global_product_presentation_id": "<PRES_CAJA_X100>",
  "identifier_type": "EAN",
  "value": "7707355052038",
  "canonical_value": "07707355052038",
  "is_primary": false
}
```

**Guardar:** `id` → `<ID_EAN_2>`

---

> Si el mismo código ya está registrado en **otro** producto, responde `409 IDENTIFIER_COLLISION` con el producto que lo tiene: hay que revisar cuál de los dos está mal, no forzar el registro.

---

[← Paso anterior](10-crear-presentaciones.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](12-crear-y-asignar-grupos.md)
