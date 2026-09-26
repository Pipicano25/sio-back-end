# Paso 03 de 11 — Crear las categorías

Ejercicio 4 — Aguja hipodérmica 18G x 1½" Rymco, caja x 100 · [← Paso anterior](02-crear-unidad-pulgada.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](04-crear-atributos.md)

**Objetivo:** Crear `DISPOSITIVOS_MEDICOS > AGUJAS_HIPODERMICAS`.

**Deja guardado para los siguientes pasos:** `<CAT_DISPOSITIVOS_MEDICOS>`, `<CAT_AGUJAS>`

---

## 1. Crear la categoría raíz `DISPOSITIVOS_MEDICOS`

```http
POST /api/v1/categories
```

```json
{
  "code": "DISPOSITIVOS_MEDICOS",
  "name": "Dispositivos médicos"
}
```

**Permiso que exige la URL:** `perm:product-catalog:categories:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `create`

**Por qué se hace así**

- `Nombre Tipo Producto = HOSPITALARIOS` es un nombre comercial del sistema anterior; la clase de producto es dispositivo médico.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<CAT_DISPOSITIVOS_MEDICOS>",
  "code": "DISPOSITIVOS_MEDICOS",
  "name": "Dispositivos médicos",
  "parent_category_id": null
}
```

**Guardar:** `id` → `<CAT_DISPOSITIVOS_MEDICOS>`

## 2. Crear la subcategoría `AGUJAS_HIPODERMICAS`

```http
POST /api/v1/categories
```

```json
{
  "code": "AGUJAS_HIPODERMICAS",
  "name": "Agujas hipodérmicas",
  "parent_category_id": "<CAT_DISPOSITIVOS_MEDICOS>"
}
```

**Permiso que exige la URL:** `perm:product-catalog:categories:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `create`

**Por qué se hace así**

- Categoría hoja: permite exigir calibre y longitud solo a las agujas, no a guantes o jeringas.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<CAT_AGUJAS>",
  "code": "AGUJAS_HIPODERMICAS",
  "name": "Agujas hipodérmicas",
  "parent_category_id": "<CAT_DISPOSITIVOS_MEDICOS>"
}
```

**Guardar:** `id` → `<CAT_AGUJAS>`

---

> Si alguna responde `409 DUPLICATE_CODE`, consúltela con `GET /api/v1/categories?code=<código>` y use su `id`.

---

[← Paso anterior](02-crear-unidad-pulgada.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](04-crear-atributos.md)
