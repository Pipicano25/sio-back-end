# Paso 06 de 13 — Asociar los atributos a la categoría

Ejercicio 1 — Acetaminofén Adorem 500 mg, caja x 100 · [← Paso anterior](05-crear-atributos.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](07-crear-producto.md)

**Objetivo:** Indicar qué atributos usan los productos de `MEDICAMENTOS_ETICOS` y cuáles son obligatorios.

**Necesita (de pasos anteriores):** `<CAT_MEDICAMENTOS_ETICOS>`, `<ATR_PRINCIPIO_ACTIVO>`, `<ATR_CONCENTRACION_MG>`, `<ATR_FORMA_FARMACEUTICA>` — pasos [04](04-crear-categorias.md), [05](05-crear-atributos.md)

**Deja guardado para los siguientes pasos:** `<CA_PRINCIPIO_ACTIVO>`, `<CA_CONCENTRACION_MG>`, `<CA_FORMA_FARMACEUTICA>`

---

## 1. Asociar `PRINCIPIO_ACTIVO` (obligatorio)

```http
POST /api/v1/categories/<CAT_MEDICAMENTOS_ETICOS>/attributes
```

```json
{
  "attribute_definition_id": "<ATR_PRINCIPIO_ACTIVO>",
  "is_required": true,
  "is_filterable": false,
  "display_order": 1
}
```

**Permiso que exige la URL:** `perm:product-catalog:categories:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Asociar un atributo a una categoría modifica la categoría: exige `update`.

**Por qué se hace así**

- `is_required: true`: todo medicamento ético debe decir su principio activo; si falta, el producto queda **incompleto**.
- `is_filterable: false`: al ser texto libre, se busca mejor con `search` que con filtros exactos.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<CA_PRINCIPIO_ACTIVO>",
  "global_category_id": "<CAT_MEDICAMENTOS_ETICOS>",
  "attribute_definition_id": "<ATR_PRINCIPIO_ACTIVO>",
  "is_required": true,
  "is_filterable": false,
  "display_order": 1
}
```

**Guardar:** `id` → `<CA_PRINCIPIO_ACTIVO>`

## 2. Asociar `CONCENTRACION_MG` (obligatorio y filtrable)

```http
POST /api/v1/categories/<CAT_MEDICAMENTOS_ETICOS>/attributes
```

```json
{
  "attribute_definition_id": "<ATR_CONCENTRACION_MG>",
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

- `is_filterable: true` permite buscar, por ejemplo, todos los productos de 500 mg (`attribute_filters=CONCENTRACION_MG:500`).

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<CA_CONCENTRACION_MG>",
  "attribute_definition_id": "<ATR_CONCENTRACION_MG>",
  "is_required": true,
  "is_filterable": true,
  "display_order": 2
}
```

**Guardar:** `id` → `<CA_CONCENTRACION_MG>`

## 3. Asociar `FORMA_FARMACEUTICA` (obligatorio y filtrable)

```http
POST /api/v1/categories/<CAT_MEDICAMENTOS_ETICOS>/attributes
```

```json
{
  "attribute_definition_id": "<ATR_FORMA_FARMACEUTICA>",
  "is_required": true,
  "is_filterable": true,
  "display_order": 3
}
```

**Permiso que exige la URL:** `perm:product-catalog:categories:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Asociar un atributo a una categoría modifica la categoría: exige `update`.

**Por qué se hace así**

- Permite filtrar por tableta, cápsula, etc.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<CA_FORMA_FARMACEUTICA>",
  "attribute_definition_id": "<ATR_FORMA_FARMACEUTICA>",
  "is_required": true,
  "is_filterable": true,
  "display_order": 3
}
```

**Guardar:** `id` → `<CA_FORMA_FARMACEUTICA>`

---

> **No hay herencia entre niveles**: si los atributos se asociaran solo a `MEDICAMENTOS`, no aplicarían a productos clasificados en `MEDICAMENTOS_ETICOS`. Se asocian a la categoría donde se clasifica el producto.

---

[← Paso anterior](05-crear-atributos.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](07-crear-producto.md)
