# Paso 08 de 13 — Clasificar el producto en su categoría

Ejercicio 1 — Acetaminofén Adorem 500 mg, caja x 100 · [← Paso anterior](07-crear-producto.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](09-registrar-valores-de-atributos.md)

**Objetivo:** Asignar la categoría principal y ver qué atributos quedan exigidos.

**Necesita (de pasos anteriores):** `<PRODUCTO>`, `<CAT_MEDICAMENTOS_ETICOS>` — pasos [04](04-crear-categorias.md), [07](07-crear-producto.md)

**Deja guardado para los siguientes pasos:** `<PC_ETICOS>`

---

## 1. Asignar la categoría `MEDICAMENTOS_ETICOS`

```http
POST /api/v1/products/<PRODUCTO>/categories
```

```json
{
  "global_category_id": "<CAT_MEDICAMENTOS_ETICOS>"
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Todo lo que se agrega **dentro** de un producto (categorías, valores, presentaciones, códigos, grupos, imágenes) exige `update` sobre `products`.

**Por qué se hace así**

- La **primera** categoría asignada queda automáticamente como principal (`is_primary: true`).
- Un producto completo necesita exactamente una categoría principal.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<PC_ETICOS>",
  "global_category_id": "<CAT_MEDICAMENTOS_ETICOS>",
  "is_primary": true,
  "status": "ACTIVE"
}
```

**Guardar:** `id` → `<PC_ETICOS>`

## 2. Consultar los atributos que ahora aplican

```http
GET /api/v1/products/<PRODUCTO>/applicable-attributes
```

**Permiso que exige la URL:** `perm:product-catalog:products:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:product-catalog:all:read`), `ventas.test` (por `perm:product-catalog:all:read`), `inventario.test` (por `perm:product-catalog:all:read`), `reportes.test` (por `perm:product-catalog:products:read`), `consulta.test` (por `perm:product-catalog:products:read`)

**Por qué se hace así**

- Confirma qué atributos pide la categoría y cuáles son obligatorios antes de registrar valores.

**Respuesta esperada — `200 OK`** (abreviada)

```json
[
  {
    "code": "PRINCIPIO_ACTIVO",
    "data_type": "TEXT",
    "is_required": true,
    "is_filterable": false
  },
  {
    "code": "CONCENTRACION_MG",
    "data_type": "DECIMAL",
    "is_required": true,
    "is_filterable": true
  },
  {
    "code": "FORMA_FARMACEUTICA",
    "data_type": "OPTION",
    "is_required": true,
    "is_filterable": true
  }
]
```

## 3. Consultar la completitud

```http
GET /api/v1/products/<PRODUCTO>/completeness
```

**Permiso que exige la URL:** `perm:product-catalog:products:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:product-catalog:all:read`), `ventas.test` (por `perm:product-catalog:all:read`), `inventario.test` (por `perm:product-catalog:all:read`), `reportes.test` (por `perm:product-catalog:products:read`), `consulta.test` (por `perm:product-catalog:products:read`)

**Por qué se hace así**

- Ya no aparece `NO_ACTIVE_CATEGORY`; ahora falta registrar los atributos obligatorios (`MISSING_REQUIRED_ATTRIBUTE`) y crear una presentación.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "is_complete": false,
  "issues": [
    "MISSING_REQUIRED_ATTRIBUTE",
    "NO_ACTIVE_PRESENTATION"
  ],
  "missing_attribute_definition_ids": [
    "<ATR_CONCENTRACION_MG>",
    "<ATR_FORMA_FARMACEUTICA>",
    "<ATR_PRINCIPIO_ACTIVO>"
  ]
}
```

---

[← Paso anterior](07-crear-producto.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](09-registrar-valores-de-atributos.md)
