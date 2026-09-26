# Paso 04 de 13 — Crear las categorías

Ejercicio 1 — Acetaminofén Adorem 500 mg, caja x 100 · [← Paso anterior](03-crear-marca.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](05-crear-atributos.md)

**Objetivo:** Crear el árbol `MEDICAMENTOS > MEDICAMENTOS_ETICOS` donde se clasifica el producto.

**Deja guardado para los siguientes pasos:** `<CAT_MEDICAMENTOS>`, `<CAT_MEDICAMENTOS_ETICOS>`

---

## 1. Crear la categoría raíz `MEDICAMENTOS`

```http
POST /api/v1/categories
```

```json
{
  "code": "MEDICAMENTOS",
  "name": "Medicamentos",
  "description": "Productos farmacéuticos."
}
```

**Permiso que exige la URL:** `perm:product-catalog:categories:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `create`

**Por qué se hace así**

- Es la raíz del árbol: no lleva `parent_category_id`.
- Agrupa éticos, genéricos y populares, que en el Excel son valores distintos de `Nombre Tipo Producto`.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<CAT_MEDICAMENTOS>",
  "code": "MEDICAMENTOS",
  "name": "Medicamentos",
  "parent_category_id": null,
  "status": "ACTIVE"
}
```

**Guardar:** `id` → `<CAT_MEDICAMENTOS>`

## 2. Crear la subcategoría `MEDICAMENTOS_ETICOS`

```http
POST /api/v1/categories
```

```json
{
  "code": "MEDICAMENTOS_ETICOS",
  "name": "Medicamentos éticos",
  "parent_category_id": "<CAT_MEDICAMENTOS>"
}
```

**Permiso que exige la URL:** `perm:product-catalog:categories:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `create`

**Por qué se hace así**

- Sale de `Nombre Tipo Producto = ETICOS`.
- `parent_category_id` la cuelga de `MEDICAMENTOS`.
- El producto se clasifica en la categoría **hoja** (`MEDICAMENTOS_ETICOS`) porque es la más precisa.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<CAT_MEDICAMENTOS_ETICOS>",
  "code": "MEDICAMENTOS_ETICOS",
  "name": "Medicamentos éticos",
  "parent_category_id": "<CAT_MEDICAMENTOS>",
  "status": "ACTIVE"
}
```

**Guardar:** `id` → `<CAT_MEDICAMENTOS_ETICOS>`

---

> Si alguna categoría responde `409 DUPLICATE_CODE`, ya existe: consúltela con `GET /api/v1/categories?code=<código>` y use su `id`.

---

[← Paso anterior](03-crear-marca.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](05-crear-atributos.md)
