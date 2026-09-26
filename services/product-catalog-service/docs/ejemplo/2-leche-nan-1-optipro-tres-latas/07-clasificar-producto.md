# Paso 07 de 12 — Clasificar el producto

Ejercicio 2 — Leche NAN 1 Optipro: tres filas del Excel, un solo producto · [← Paso anterior](06-crear-producto.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](08-registrar-valores-de-atributos.md)

**Objetivo:** Asignar la categoría `LECHES`.

**Necesita (de pasos anteriores):** `<PRODUCTO>`, `<CAT_LECHES>` — pasos [03](03-crear-categorias.md), [06](06-crear-producto.md)

**Deja guardado para los siguientes pasos:** `<PC_LECHES>`

---

## 1. Asignar la categoría `LECHES`

```http
POST /api/v1/products/<PRODUCTO>/categories
```

```json
{
  "global_category_id": "<CAT_LECHES>"
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Todo lo que se agrega **dentro** de un producto (categorías, valores, presentaciones, códigos, grupos, imágenes) exige `update` sobre `products`.

**Por qué se hace así**

- Primera categoría → queda como principal automáticamente.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<PC_LECHES>",
  "global_category_id": "<CAT_LECHES>",
  "is_primary": true
}
```

**Guardar:** `id` → `<PC_LECHES>`

---

[← Paso anterior](06-crear-producto.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](08-registrar-valores-de-atributos.md)
