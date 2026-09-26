# Paso 09 de 12 — Crear las tres presentaciones

Ejercicio 2 — Leche NAN 1 Optipro: tres filas del Excel, un solo producto · [← Paso anterior](08-registrar-valores-de-atributos.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](10-registrar-codigos-de-barras.md)

**Objetivo:** Una presentación por cada fila del Excel.

**Necesita (de pasos anteriores):** `<PRODUCTO>`, `<CAN>` — pasos [01](01-consultar-datos-base.md), [06](06-crear-producto.md)

**Deja guardado para los siguientes pasos:** `<PRES_LATA_400G>`, `<PRES_LATA_900G>`, `<PRES_LATA_1100G>`

---

## 1. Presentación `LATA_400G` (fila 7334)

```http
POST /api/v1/products/<PRODUCTO>/presentations
```

```json
{
  "code": "LATA_400G",
  "name": "Lata x 400 g",
  "packaging_type_id": "<CAN>",
  "base_quantity": 400,
  "display_order": 1,
  "is_base": false
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Todo lo que se agrega **dentro** de un producto (categorías, valores, presentaciones, códigos, grupos, imágenes) exige `update` sobre `products`.

**Por qué se hace así**

- `base_quantity: 400` porque la unidad base es el gramo: una lata = 400 g.
- `is_base: false`: una presentación base debe tener `base_quantity = 1` (1 g), y ninguna lata pesa 1 g. Un producto **no necesita** presentación base para estar completo.
- No se envía `content_quantity`: con la unidad base en gramos, `base_quantity` ya dice cuánto contiene.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<PRES_LATA_400G>",
  "code": "LATA_400G",
  "name": "Lata x 400 g",
  "base_quantity": "400.00000000",
  "is_base": false,
  "eligible_for_adoption": true
}
```

**Guardar:** `id` → `<PRES_LATA_400G>`

## 2. Presentación `LATA_900G` (fila 6138)

```http
POST /api/v1/products/<PRODUCTO>/presentations
```

```json
{
  "code": "LATA_900G",
  "name": "Lata x 900 g",
  "packaging_type_id": "<CAN>",
  "base_quantity": 900,
  "display_order": 2,
  "is_base": false
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Todo lo que se agrega **dentro** de un producto (categorías, valores, presentaciones, códigos, grupos, imágenes) exige `update` sobre `products`.

**Por qué se hace así**

- Misma lógica: 900 g.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<PRES_LATA_900G>",
  "code": "LATA_900G",
  "base_quantity": "900.00000000",
  "is_base": false
}
```

**Guardar:** `id` → `<PRES_LATA_900G>`

## 3. Presentación `LATA_1100G` (fila 7333)

```http
POST /api/v1/products/<PRODUCTO>/presentations
```

```json
{
  "code": "LATA_1100G",
  "name": "Lata x 1100 g",
  "packaging_type_id": "<CAN>",
  "base_quantity": 1100,
  "display_order": 3,
  "is_base": false
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Todo lo que se agrega **dentro** de un producto (categorías, valores, presentaciones, códigos, grupos, imágenes) exige `update` sobre `products`.

**Por qué se hace así**

- Misma lógica: 1100 g. `display_order` ordena de menor a mayor tamaño.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<PRES_LATA_1100G>",
  "code": "LATA_1100G",
  "base_quantity": "1100.00000000",
  "is_base": false
}
```

**Guardar:** `id` → `<PRES_LATA_1100G>`

---

[← Paso anterior](08-registrar-valores-de-atributos.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](10-registrar-codigos-de-barras.md)
