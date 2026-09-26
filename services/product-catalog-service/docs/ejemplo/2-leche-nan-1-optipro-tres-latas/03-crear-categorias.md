# Paso 03 de 12 — Crear las categorías

Ejercicio 2 — Leche NAN 1 Optipro: tres filas del Excel, un solo producto · [← Paso anterior](02-crear-marca.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](04-crear-atributos.md)

**Objetivo:** Crear `ALIMENTOS > LECHES`.

**Deja guardado para los siguientes pasos:** `<CAT_ALIMENTOS>`, `<CAT_LECHES>`

---

## 1. Crear la categoría raíz `ALIMENTOS`

```http
POST /api/v1/categories
```

```json
{
  "code": "ALIMENTOS",
  "name": "Alimentos"
}
```

**Permiso que exige la URL:** `perm:product-catalog:categories:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `create`

**Por qué se hace así**

- Raíz para leches y otros alimentos (`Grupo 1 = ALIMENTOS` en el Excel lo confirma).

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<CAT_ALIMENTOS>",
  "code": "ALIMENTOS",
  "name": "Alimentos",
  "parent_category_id": null
}
```

**Guardar:** `id` → `<CAT_ALIMENTOS>`

## 2. Crear la subcategoría `LECHES`

```http
POST /api/v1/categories
```

```json
{
  "code": "LECHES",
  "name": "Leches y fórmulas lácteas",
  "parent_category_id": "<CAT_ALIMENTOS>"
}
```

**Permiso que exige la URL:** `perm:product-catalog:categories:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `create`

**Por qué se hace así**

- Sale de `Nombre Tipo Producto = LECHES`. Incluye fórmulas infantiles (NAN, Enfamil) y leches en polvo (Klim).

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<CAT_LECHES>",
  "code": "LECHES",
  "name": "Leches y fórmulas lácteas",
  "parent_category_id": "<CAT_ALIMENTOS>"
}
```

**Guardar:** `id` → `<CAT_LECHES>`

---

> Si alguna responde `409 DUPLICATE_CODE`, consúltela con `GET /api/v1/categories?code=<código>` y use su `id`.

---

[← Paso anterior](02-crear-marca.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](04-crear-atributos.md)
