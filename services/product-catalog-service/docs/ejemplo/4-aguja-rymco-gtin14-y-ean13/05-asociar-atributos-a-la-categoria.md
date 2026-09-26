# Paso 05 de 11 — Asociar los atributos a la categoría

Ejercicio 4 — Aguja hipodérmica 18G x 1½" Rymco, caja x 100 · [← Paso anterior](04-crear-atributos.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](06-crear-producto.md)

**Objetivo:** Ambos obligatorios y filtrables.

**Necesita (de pasos anteriores):** `<CAT_AGUJAS>`, `<ATR_CALIBRE_AGUJA>`, `<ATR_LONGITUD_AGUJA>` — pasos [03](03-crear-categorias.md), [04](04-crear-atributos.md)

**Deja guardado para los siguientes pasos:** `<CA_CALIBRE>`, `<CA_LONGITUD>`

---

## 1. Asociar `CALIBRE_AGUJA`

```http
POST /api/v1/categories/<CAT_AGUJAS>/attributes
```

```json
{
  "attribute_definition_id": "<ATR_CALIBRE_AGUJA>",
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

- Sin calibre no se puede despachar una aguja: obligatorio. Filtrable para buscar "agujas 18G".

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<CA_CALIBRE>",
  "attribute_definition_id": "<ATR_CALIBRE_AGUJA>",
  "is_required": true,
  "is_filterable": true
}
```

**Guardar:** `id` → `<CA_CALIBRE>`

## 2. Asociar `LONGITUD_AGUJA`

```http
POST /api/v1/categories/<CAT_AGUJAS>/attributes
```

```json
{
  "attribute_definition_id": "<ATR_LONGITUD_AGUJA>",
  "is_required": true,
  "is_filterable": true,
  "display_order": 2
}
```

**Permiso que exige la URL:** `perm:product-catalog:categories:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Asociar un atributo a una categoría modifica la categoría: exige `update`.

**Por qué se hace así**

- Mismo criterio que el calibre.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<CA_LONGITUD>",
  "attribute_definition_id": "<ATR_LONGITUD_AGUJA>",
  "is_required": true,
  "is_filterable": true
}
```

**Guardar:** `id` → `<CA_LONGITUD>`

---

[← Paso anterior](04-crear-atributos.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](06-crear-producto.md)
