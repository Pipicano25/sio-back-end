# Paso 08 de 12 — Registrar los valores de los atributos

Ejercicio 3 — Pañal Winny Gold etapa 6 XXXG, paquete x 30 · [← Paso anterior](07-clasificar-producto.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](09-crear-presentacion.md)

**Objetivo:** Talla XXXG y etapa 6.

**Necesita (de pasos anteriores):** `<PRODUCTO>`, `<ATR_TALLA_PANAL>`, `<OPC_TALLA_XXXG>`, `<ATR_ETAPA_PANAL>` — pasos [04](04-crear-atributos.md), [06](06-crear-producto.md)

---

## 1. Talla = XXXG

```http
PUT /api/v1/products/<PRODUCTO>/attribute-values/<ATR_TALLA_PANAL>
```

```json
{
  "option_id": "<OPC_TALLA_XXXG>"
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Todo lo que se agrega **dentro** de un producto (categorías, valores, presentaciones, códigos, grupos, imágenes) exige `update` sobre `products`.

**Por qué se hace así**

- Se envía el `id` de la opción `XXXG`, no el texto.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "attribute_definition_id": "<ATR_TALLA_PANAL>",
  "option_id": "<OPC_TALLA_XXXG>",
  "version": 1
}
```

## 2. Etapa = 6

```http
PUT /api/v1/products/<PRODUCTO>/attribute-values/<ATR_ETAPA_PANAL>
```

```json
{
  "integer_value": 6
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
  "attribute_definition_id": "<ATR_ETAPA_PANAL>",
  "integer_value": 6,
  "version": 1
}
```

---

[← Paso anterior](07-clasificar-producto.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](09-crear-presentacion.md)
