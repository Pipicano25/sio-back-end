# Paso 03 de 12 — Crear las categorías

Ejercicio 3 — Pañal Winny Gold etapa 6 XXXG, paquete x 30 · [← Paso anterior](02-crear-marca.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](04-crear-atributos.md)

**Objetivo:** Crear `CUIDADO_BEBE > PANALES_BEBE`.

**Deja guardado para los siguientes pasos:** `<CAT_CUIDADO_BEBE>`, `<CAT_PANALES_BEBE>`

---

## 1. Crear la categoría raíz `CUIDADO_BEBE`

```http
POST /api/v1/categories
```

```json
{
  "code": "CUIDADO_BEBE",
  "name": "Cuidado del bebé"
}
```

**Permiso que exige la URL:** `perm:product-catalog:categories:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `create`

**Por qué se hace así**

- Raíz para pañales, pañitos y otros productos de bebé. El Excel los tiene en `ASEO Y LIMPIEZA`, que es demasiado amplio para clasificar.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<CAT_CUIDADO_BEBE>",
  "code": "CUIDADO_BEBE",
  "name": "Cuidado del bebé",
  "parent_category_id": null
}
```

**Guardar:** `id` → `<CAT_CUIDADO_BEBE>`

## 2. Crear la subcategoría `PANALES_BEBE`

```http
POST /api/v1/categories
```

```json
{
  "code": "PANALES_BEBE",
  "name": "Pañales para bebé",
  "parent_category_id": "<CAT_CUIDADO_BEBE>"
}
```

**Permiso que exige la URL:** `perm:product-catalog:categories:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `create`

**Por qué se hace así**

- Sale de `Nombre Tipo Producto = PAÑALES`.
- El código va **sin Ñ ni tildes** (`PANALES_BEBE`); el nombre sí las lleva.
- Se separa de los pañales de adulto (Tena), que usan otras tallas.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<CAT_PANALES_BEBE>",
  "code": "PANALES_BEBE",
  "name": "Pañales para bebé",
  "parent_category_id": "<CAT_CUIDADO_BEBE>"
}
```

**Guardar:** `id` → `<CAT_PANALES_BEBE>`

---

> Si alguna responde `409 DUPLICATE_CODE`, consúltela con `GET /api/v1/categories?code=<código>` y use su `id`.

---

[← Paso anterior](02-crear-marca.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](04-crear-atributos.md)
