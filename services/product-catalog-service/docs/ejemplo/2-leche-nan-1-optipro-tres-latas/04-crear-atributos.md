# Paso 04 de 12 — Crear las definiciones de atributo

Ejercicio 2 — Leche NAN 1 Optipro: tres filas del Excel, un solo producto · [← Paso anterior](03-crear-categorias.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](05-asociar-atributos-a-la-categoria.md)

**Objetivo:** Definir la etapa de la fórmula y si es fórmula infantil.

**Deja guardado para los siguientes pasos:** `<ATR_ETAPA_FORMULA>`, `<ATR_FORMULA_INFANTIL>`

---

## 1. Crear el atributo `ETAPA_FORMULA` (entero)

```http
POST /api/v1/attribute-definitions
```

```json
{
  "code": "ETAPA_FORMULA",
  "name": "Etapa de la fórmula",
  "description": "Etapa de alimentación a la que corresponde la fórmula (1, 2, 3…).",
  "data_type": "INTEGER"
}
```

**Permiso que exige la URL:** `perm:product-catalog:attribute-definitions:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `create`

**Por qué se hace así**

- `INTEGER` porque la etapa es un número entero: "NAN **1**", "NAN **2**"…
- Sin `unit_of_measure_id`: la etapa no es una magnitud física.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<ATR_ETAPA_FORMULA>",
  "code": "ETAPA_FORMULA",
  "data_type": "INTEGER",
  "unit_of_measure_id": null
}
```

**Guardar:** `id` → `<ATR_ETAPA_FORMULA>`

## 2. Crear el atributo `FORMULA_INFANTIL` (sí/no)

```http
POST /api/v1/attribute-definitions
```

```json
{
  "code": "FORMULA_INFANTIL",
  "name": "Fórmula infantil",
  "description": "Indica si el producto es una fórmula para lactantes o niños pequeños.",
  "data_type": "BOOLEAN"
}
```

**Permiso que exige la URL:** `perm:product-catalog:attribute-definitions:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `create`

**Por qué se hace así**

- `BOOLEAN` porque la respuesta es sí o no. Separa fórmulas infantiles (NAN) de leches generales (Klim) dentro de `LECHES`.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<ATR_FORMULA_INFANTIL>",
  "code": "FORMULA_INFANTIL",
  "data_type": "BOOLEAN"
}
```

**Guardar:** `id` → `<ATR_FORMULA_INFANTIL>`

---

[← Paso anterior](03-crear-categorias.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](05-asociar-atributos-a-la-categoria.md)
