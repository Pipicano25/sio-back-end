# Paso 08 de 12 — Registrar los valores de los atributos

Ejercicio 2 — Leche NAN 1 Optipro: tres filas del Excel, un solo producto · [← Paso anterior](07-clasificar-producto.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](09-crear-presentaciones.md)

**Objetivo:** Etapa 1 y fórmula infantil = sí.

**Necesita (de pasos anteriores):** `<PRODUCTO>`, `<ATR_FORMULA_INFANTIL>`, `<ATR_ETAPA_FORMULA>` — pasos [04](04-crear-atributos.md), [06](06-crear-producto.md)

---

## 1. Fórmula infantil = sí

```http
PUT /api/v1/products/<PRODUCTO>/attribute-values/<ATR_FORMULA_INFANTIL>
```

```json
{
  "boolean_value": true
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Todo lo que se agrega **dentro** de un producto (categorías, valores, presentaciones, códigos, grupos, imágenes) exige `update` sobre `products`.

**Por qué se hace así**

- `BOOLEAN` → `boolean_value` con `true` o `false` (no `"S"`/`"N"` como en el Excel).

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "attribute_definition_id": "<ATR_FORMULA_INFANTIL>",
  "boolean_value": true,
  "version": 1
}
```

## 2. Etapa = 1

```http
PUT /api/v1/products/<PRODUCTO>/attribute-values/<ATR_ETAPA_FORMULA>
```

```json
{
  "integer_value": 1
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Todo lo que se agrega **dentro** de un producto (categorías, valores, presentaciones, códigos, grupos, imágenes) exige `update` sobre `products`.

**Por qué se hace así**

- `INTEGER` → `integer_value`. Si se enviara `1.5` o `"1"` en `text_value` respondería `422 VALUE_TYPE_MISMATCH`.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "attribute_definition_id": "<ATR_ETAPA_FORMULA>",
  "integer_value": 1,
  "version": 1
}
```

---

[← Paso anterior](07-clasificar-producto.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](09-crear-presentaciones.md)
