# Paso 04 de 11 — Crear los atributos

Ejercicio 4 — Aguja hipodérmica 18G x 1½" Rymco, caja x 100 · [← Paso anterior](03-crear-categorias.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](05-asociar-atributos-a-la-categoria.md)

**Objetivo:** Calibre y longitud de la aguja.

**Necesita (de pasos anteriores):** `<PULG>` — pasos [02](02-crear-unidad-pulgada.md)

**Deja guardado para los siguientes pasos:** `<ATR_CALIBRE_AGUJA>`, `<ATR_LONGITUD_AGUJA>`

---

## 1. Crear el atributo `CALIBRE_AGUJA` (entero, sin unidad)

```http
POST /api/v1/attribute-definitions
```

```json
{
  "code": "CALIBRE_AGUJA",
  "name": "Calibre (G)",
  "description": "Calibre de la aguja en la escala gauge; a mayor número, aguja más delgada.",
  "data_type": "INTEGER"
}
```

**Permiso que exige la URL:** `perm:product-catalog:attribute-definitions:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `create`

**Por qué se hace así**

- `18G` es el calibre en la escala **gauge**: un número entero de una escala, no una magnitud física.
- Por eso no lleva `unit_of_measure_id`: la "G" de 18G **no** es gramos.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<ATR_CALIBRE_AGUJA>",
  "code": "CALIBRE_AGUJA",
  "data_type": "INTEGER",
  "unit_of_measure_id": null
}
```

**Guardar:** `id` → `<ATR_CALIBRE_AGUJA>`

## 2. Crear el atributo `LONGITUD_AGUJA` (decimal en pulgadas)

```http
POST /api/v1/attribute-definitions
```

```json
{
  "code": "LONGITUD_AGUJA",
  "name": "Longitud",
  "description": "Longitud de la aguja en pulgadas.",
  "data_type": "DECIMAL",
  "unit_of_measure_id": "<PULG>"
}
```

**Permiso que exige la URL:** `perm:product-catalog:attribute-definitions:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `create`

**Por qué se hace así**

- `DECIMAL` con unidad `PULG`: `1 1/2` se guarda como `1.5`.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<ATR_LONGITUD_AGUJA>",
  "code": "LONGITUD_AGUJA",
  "data_type": "DECIMAL",
  "unit_of_measure_id": "<PULG>"
}
```

**Guardar:** `id` → `<ATR_LONGITUD_AGUJA>`

---

[← Paso anterior](03-crear-categorias.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](05-asociar-atributos-a-la-categoria.md)
