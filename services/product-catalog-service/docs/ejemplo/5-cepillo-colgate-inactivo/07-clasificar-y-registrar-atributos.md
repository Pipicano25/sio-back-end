# Paso 07 de 13 — Clasificar y registrar atributos

Ejercicio 5 — Cepillo Colgate infantil pack x 2 (producto inactivo) · [← Paso anterior](06-crear-producto.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](08-crear-presentacion.md)

**Objetivo:** Asignar la categoría y dar valor a los atributos.

**Necesita (de pasos anteriores):** `<PRODUCTO>`, `<CAT_CEPILLOS>`, `<ATR_DUREZA_CERDAS>`, `<OPC_EXTRA_SUAVE>`, `<ATR_RANGO_EDAD>` — pasos [03](03-crear-categorias.md), [04](04-crear-atributos.md), [06](06-crear-producto.md)

**Deja guardado para los siguientes pasos:** `<PC_CEPILLOS>`

---

## 1. Asignar la categoría `CEPILLOS_DENTALES`

```http
POST /api/v1/products/<PRODUCTO>/categories
```

```json
{
  "global_category_id": "<CAT_CEPILLOS>"
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Todo lo que se agrega **dentro** de un producto (categorías, valores, presentaciones, códigos, grupos, imágenes) exige `update` sobre `products`.

**Por qué se hace así**

- Primera categoría → principal. Debe ir **antes** de los atributos: un atributo solo se puede registrar si alguna categoría del producto lo usa (si no, `422 ATTRIBUTE_NOT_APPLICABLE`).

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<PC_CEPILLOS>",
  "global_category_id": "<CAT_CEPILLOS>",
  "is_primary": true
}
```

**Guardar:** `id` → `<PC_CEPILLOS>`

## 2. Dureza = Extra suave

```http
PUT /api/v1/products/<PRODUCTO>/attribute-values/<ATR_DUREZA_CERDAS>
```

```json
{
  "option_id": "<OPC_EXTRA_SUAVE>"
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Todo lo que se agrega **dentro** de un producto (categorías, valores, presentaciones, códigos, grupos, imágenes) exige `update` sobre `products`.

**Por qué se hace así**

- `OPTION` → `option_id`.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "attribute_definition_id": "<ATR_DUREZA_CERDAS>",
  "option_id": "<OPC_EXTRA_SUAVE>"
}
```

## 3. Rango de edad = 2 a 5 años

```http
PUT /api/v1/products/<PRODUCTO>/attribute-values/<ATR_RANGO_EDAD>
```

```json
{
  "text_value": "2 a 5 años"
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Todo lo que se agrega **dentro** de un producto (categorías, valores, presentaciones, códigos, grupos, imágenes) exige `update` sobre `products`.

**Por qué se hace así**

- Aunque es opcional, el dato existe en el nombre del Excel (`2-5 AÑOS`) y se registra.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "attribute_definition_id": "<ATR_RANGO_EDAD>",
  "text_value": "2 a 5 años"
}
```

---

[← Paso anterior](06-crear-producto.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](08-crear-presentacion.md)
