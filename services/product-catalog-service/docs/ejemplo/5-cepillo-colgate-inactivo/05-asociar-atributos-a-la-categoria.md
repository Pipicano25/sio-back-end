# Paso 05 de 14 — Asociar los atributos a la categoría

Ejercicio 5 — Cepillo Colgate infantil pack x 2 (producto inactivo) · [← Paso anterior](04-crear-atributos.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](06-crear-producto.md)

**Objetivo:** Dureza obligatoria y filtrable; rango de edad opcional.

**Necesita (de pasos anteriores):** `<CAT_CEPILLOS>`, `<ATR_DUREZA_CERDAS>`, `<ATR_RANGO_EDAD>` — pasos [03](03-crear-categorias.md), [04](04-crear-atributos.md)

**Deja guardado para los siguientes pasos:** `<CA_DUREZA>`, `<CA_RANGO_EDAD>`

---

## 1. Asociar `DUREZA_CERDAS`

```http
POST /api/v1/categories/<CAT_CEPILLOS>/attributes
```

```json
{
  "attribute_definition_id": "<ATR_DUREZA_CERDAS>",
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

- Todo cepillo declara su dureza.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<CA_DUREZA>",
  "attribute_definition_id": "<ATR_DUREZA_CERDAS>",
  "is_required": true,
  "is_filterable": true
}
```

**Guardar:** `id` → `<CA_DUREZA>`

## 2. Asociar `RANGO_EDAD`

```http
POST /api/v1/categories/<CAT_CEPILLOS>/attributes
```

```json
{
  "attribute_definition_id": "<ATR_RANGO_EDAD>",
  "is_required": false,
  "is_filterable": false,
  "display_order": 2
}
```

**Permiso que exige la URL:** `perm:product-catalog:categories:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Asociar un atributo a una categoría modifica la categoría: exige `update`.

**Por qué se hace así**

- Opcional: los cepillos de adulto no indican edad.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<CA_RANGO_EDAD>",
  "attribute_definition_id": "<ATR_RANGO_EDAD>",
  "is_required": false,
  "is_filterable": false
}
```

**Guardar:** `id` → `<CA_RANGO_EDAD>`

---

[← Paso anterior](04-crear-atributos.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](06-crear-producto.md)
