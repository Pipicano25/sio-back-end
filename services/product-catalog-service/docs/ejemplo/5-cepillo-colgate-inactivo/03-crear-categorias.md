# Paso 03 de 14 — Crear las categorías

Ejercicio 5 — Cepillo Colgate infantil pack x 2 (producto inactivo) · [← Paso anterior](02-crear-marca.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](04-crear-atributos.md)

**Objetivo:** Crear `CUIDADO_ORAL > CEPILLOS_DENTALES`.

**Deja guardado para los siguientes pasos:** `<CAT_CUIDADO_ORAL>`, `<CAT_CEPILLOS>`

---

## 1. Crear la categoría raíz `CUIDADO_ORAL`

```http
POST /api/v1/categories
```

```json
{
  "code": "CUIDADO_ORAL",
  "name": "Cuidado oral"
}
```

**Permiso que exige la URL:** `perm:product-catalog:categories:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `create`

**Por qué se hace así**

- `CONSUMO` en el Excel mezcla miles de productos distintos; la categoría debe decir qué es el producto.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<CAT_CUIDADO_ORAL>",
  "code": "CUIDADO_ORAL",
  "name": "Cuidado oral",
  "parent_category_id": null
}
```

**Guardar:** `id` → `<CAT_CUIDADO_ORAL>`

## 2. Crear la subcategoría `CEPILLOS_DENTALES`

```http
POST /api/v1/categories
```

```json
{
  "code": "CEPILLOS_DENTALES",
  "name": "Cepillos dentales",
  "parent_category_id": "<CAT_CUIDADO_ORAL>"
}
```

**Permiso que exige la URL:** `perm:product-catalog:categories:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `create`

**Por qué se hace así**

- Hoja donde se clasifica el producto y donde se asocian sus atributos.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<CAT_CEPILLOS>",
  "code": "CEPILLOS_DENTALES",
  "name": "Cepillos dentales",
  "parent_category_id": "<CAT_CUIDADO_ORAL>"
}
```

**Guardar:** `id` → `<CAT_CEPILLOS>`

---

> Si alguna responde `409 DUPLICATE_CODE`, consúltela con `GET /api/v1/categories?code=<código>` y use su `id`.

---

[← Paso anterior](02-crear-marca.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](04-crear-atributos.md)
