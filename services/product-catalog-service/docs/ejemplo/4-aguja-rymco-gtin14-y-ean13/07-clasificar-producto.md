# Paso 07 de 11 — Clasificar el producto

Ejercicio 4 — Aguja hipodérmica 18G x 1½" Rymco, caja x 100 · [← Paso anterior](06-crear-producto.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](08-registrar-valores-y-presentaciones.md)

**Objetivo:** Asignar `AGUJAS_HIPODERMICAS`.

**Necesita (de pasos anteriores):** `<PRODUCTO>`, `<CAT_AGUJAS>` — pasos [03](03-crear-categorias.md), [06](06-crear-producto.md)

**Deja guardado para los siguientes pasos:** `<PC_AGUJAS>`

---

## 1. Asignar la categoría

```http
POST /api/v1/products/<PRODUCTO>/categories
```

```json
{
  "global_category_id": "<CAT_AGUJAS>"
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Todo lo que se agrega **dentro** de un producto (categorías, valores, presentaciones, códigos, grupos, imágenes) exige `update` sobre `products`.

**Por qué se hace así**

- Primera categoría → principal.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<PC_AGUJAS>",
  "global_category_id": "<CAT_AGUJAS>",
  "is_primary": true
}
```

**Guardar:** `id` → `<PC_AGUJAS>`

---

[← Paso anterior](06-crear-producto.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](08-registrar-valores-y-presentaciones.md)
