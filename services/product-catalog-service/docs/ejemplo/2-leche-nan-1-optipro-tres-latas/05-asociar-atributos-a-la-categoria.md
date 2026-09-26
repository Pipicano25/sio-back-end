# Paso 05 de 12 — Asociar los atributos a la categoría

Ejercicio 2 — Leche NAN 1 Optipro: tres filas del Excel, un solo producto · [← Paso anterior](04-crear-atributos.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](06-crear-producto.md)

**Objetivo:** Indicar cómo usa `LECHES` cada atributo.

**Necesita (de pasos anteriores):** `<CAT_LECHES>`, `<ATR_FORMULA_INFANTIL>`, `<ATR_ETAPA_FORMULA>` — pasos [03](03-crear-categorias.md), [04](04-crear-atributos.md)

**Deja guardado para los siguientes pasos:** `<CA_FORMULA_INFANTIL>`, `<CA_ETAPA_FORMULA>`

---

## 1. Asociar `FORMULA_INFANTIL` (obligatorio y filtrable)

```http
POST /api/v1/categories/<CAT_LECHES>/attributes
```

```json
{
  "attribute_definition_id": "<ATR_FORMULA_INFANTIL>",
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

- Obligatorio: toda leche debe decir si es fórmula infantil o no. Filtrable para listar solo fórmulas.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<CA_FORMULA_INFANTIL>",
  "attribute_definition_id": "<ATR_FORMULA_INFANTIL>",
  "is_required": true,
  "is_filterable": true
}
```

**Guardar:** `id` → `<CA_FORMULA_INFANTIL>`

## 2. Asociar `ETAPA_FORMULA` (opcional y filtrable)

```http
POST /api/v1/categories/<CAT_LECHES>/attributes
```

```json
{
  "attribute_definition_id": "<ATR_ETAPA_FORMULA>",
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

- `is_required: false`: una leche que no es fórmula (Klim tradicional) no tiene etapa. Si fuera obligatorio, esos productos nunca quedarían completos.
- Aunque sea opcional, se registra cuando existe.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<CA_ETAPA_FORMULA>",
  "attribute_definition_id": "<ATR_ETAPA_FORMULA>",
  "is_required": false,
  "is_filterable": true
}
```

**Guardar:** `id` → `<CA_ETAPA_FORMULA>`

---

[← Paso anterior](04-crear-atributos.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](06-crear-producto.md)
