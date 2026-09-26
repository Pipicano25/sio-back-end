# Paso 05 de 12 — Asociar los atributos a la categoría

Ejercicio 3 — Pañal Winny Gold etapa 6 XXXG, paquete x 30 · [← Paso anterior](04-crear-atributos.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](06-crear-producto.md)

**Objetivo:** La talla obligatoria y filtrable; la etapa opcional y filtrable.

**Necesita (de pasos anteriores):** `<CAT_PANALES_BEBE>`, `<ATR_TALLA_PANAL>`, `<ATR_ETAPA_PANAL>` — pasos [03](03-crear-categorias.md), [04](04-crear-atributos.md)

**Deja guardado para los siguientes pasos:** `<CA_TALLA_PANAL>`, `<CA_ETAPA_PANAL>`

---

## 1. Asociar `TALLA_PANAL` (obligatorio y filtrable)

```http
POST /api/v1/categories/<CAT_PANALES_BEBE>/attributes
```

```json
{
  "attribute_definition_id": "<ATR_TALLA_PANAL>",
  "is_required": true,
  "is_filterable": true,
  "display_order": 1
}
```

**Permiso que exige la URL:** `perm:product-catalog:categories:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Asociar un atributo a una categoría modifica la categoría: exige `update`.

**Por qué se hace así**

- Todo pañal tiene talla: sin ella el producto queda incompleto.
- Filtrable: es la búsqueda más habitual en punto de venta ("pañales talla XXXG").

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<CA_TALLA_PANAL>",
  "attribute_definition_id": "<ATR_TALLA_PANAL>",
  "is_required": true,
  "is_filterable": true
}
```

**Guardar:** `id` → `<CA_TALLA_PANAL>`

## 2. Asociar `ETAPA_PANAL` (opcional y filtrable)

```http
POST /api/v1/categories/<CAT_PANALES_BEBE>/attributes
```

```json
{
  "attribute_definition_id": "<ATR_ETAPA_PANAL>",
  "is_required": false,
  "is_filterable": true,
  "display_order": 2
}
```

**Permiso que exige la URL:** `perm:product-catalog:categories:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Asociar un atributo a una categoría modifica la categoría: exige `update`.

**Por qué se hace así**

- Opcional: no todas las marcas numeran etapas (Huggies usa etapas, otras solo talla).

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<CA_ETAPA_PANAL>",
  "attribute_definition_id": "<ATR_ETAPA_PANAL>",
  "is_required": false,
  "is_filterable": true
}
```

**Guardar:** `id` → `<CA_ETAPA_PANAL>`

---

[← Paso anterior](04-crear-atributos.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](06-crear-producto.md)
