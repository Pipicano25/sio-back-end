# Paso 08 de 13 — Crear la presentación

Ejercicio 5 — Cepillo Colgate infantil pack x 2 (producto inactivo) · [← Paso anterior](07-clasificar-y-registrar-atributos.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](09-codigo-interno-no-es-codigo-de-barras.md)

**Objetivo:** Pack x 2 cepillos.

**Necesita (de pasos anteriores):** `<PRODUCTO>`, `<PACK>` — pasos [01](01-consultar-datos-base.md), [06](06-crear-producto.md)

**Deja guardado para los siguientes pasos:** `<PRES_PACK_X2>`

---

## 1. Presentación `PACK_X2`

```http
POST /api/v1/products/<PRODUCTO>/presentations
```

```json
{
  "code": "PACK_X2",
  "name": "Pack x 2 cepillos",
  "packaging_type_id": "<PACK>",
  "base_quantity": 2,
  "display_order": 1,
  "is_base": false
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Todo lo que se agrega **dentro** de un producto (categorías, valores, presentaciones, códigos, grupos, imágenes) exige `update` sobre `products`.

**Por qué se hace así**

- `base_quantity: 2` sale del nombre (`PACK X2`); la columna `Contenido Interno` vino vacía.
- No se crea presentación unidad: el pack no se abre para vender cepillos sueltos.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<PRES_PACK_X2>",
  "code": "PACK_X2",
  "name": "Pack x 2 cepillos",
  "packaging_type_id": "<PACK>",
  "base_quantity": "2.00000000",
  "is_base": false
}
```

**Guardar:** `id` → `<PRES_PACK_X2>`

---

[← Paso anterior](07-clasificar-y-registrar-atributos.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](09-codigo-interno-no-es-codigo-de-barras.md)
