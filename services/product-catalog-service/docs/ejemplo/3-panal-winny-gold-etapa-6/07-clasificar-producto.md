# Paso 07 de 12 — Clasificar el producto

Ejercicio 3 — Pañal Winny Gold etapa 6 XXXG, paquete x 30 · [← Paso anterior](06-crear-producto.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](08-registrar-valores-de-atributos.md)

**Objetivo:** Asignar `PANALES_BEBE`.

**Necesita (de pasos anteriores):** `<PRODUCTO>`, `<CAT_PANALES_BEBE>` — pasos [03](03-crear-categorias.md), [06](06-crear-producto.md)

**Deja guardado para los siguientes pasos:** `<PC_PANALES>`

---

## 1. Asignar la categoría `PANALES_BEBE`

```http
POST /api/v1/products/<PRODUCTO>/categories
```

```json
{
  "global_category_id": "<CAT_PANALES_BEBE>"
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Todo lo que se agrega **dentro** de un producto (categorías, valores, presentaciones, códigos, grupos, imágenes) exige `update` sobre `products`.

**Por qué se hace así**

- Queda como principal por ser la primera.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<PC_PANALES>",
  "global_category_id": "<CAT_PANALES_BEBE>",
  "is_primary": true
}
```

**Guardar:** `id` → `<PC_PANALES>`

---

[← Paso anterior](06-crear-producto.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](08-registrar-valores-de-atributos.md)
