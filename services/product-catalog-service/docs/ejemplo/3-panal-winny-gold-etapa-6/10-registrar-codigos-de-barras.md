# Paso 10 de 12 — Registrar los códigos de barras

Ejercicio 3 — Pañal Winny Gold etapa 6 XXXG, paquete x 30 · [← Paso anterior](09-crear-presentacion.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](11-crear-y-asignar-grupos.md)

**Objetivo:** Los dos EAN del paquete.

**Necesita (de pasos anteriores):** `<PRODUCTO>`, `<PRES_PAQUETE_X30>` — pasos [06](06-crear-producto.md), [09](09-crear-presentacion.md)

**Deja guardado para los siguientes pasos:** `<ID_EAN_1>`, `<ID_EAN_2>`

---

## 1. EAN `7701021118264` (principal)

```http
POST /api/v1/products/<PRODUCTO>/identifiers
```

```json
{
  "identifier_type": "EAN",
  "value": "7701021118264",
  "global_product_presentation_id": "<PRES_PAQUETE_X30>",
  "is_primary": true
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Todo lo que se agrega **dentro** de un producto (categorías, valores, presentaciones, códigos, grupos, imágenes) exige `update` sobre `products`.

**Por qué se hace así**

- `Código Barras 1` del Excel, EAN-13 válido. Se liga al paquete, que es lo que se escanea.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<ID_EAN_1>",
  "identifier_type": "EAN",
  "value": "7701021118264",
  "is_primary": true
}
```

**Guardar:** `id` → `<ID_EAN_1>`

## 2. EAN `7701021118912`

```http
POST /api/v1/products/<PRODUCTO>/identifiers
```

```json
{
  "identifier_type": "EAN",
  "value": "7701021118912",
  "global_product_presentation_id": "<PRES_PAQUETE_X30>",
  "is_primary": false
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Todo lo que se agrega **dentro** de un producto (categorías, valores, presentaciones, códigos, grupos, imágenes) exige `update` sobre `products`.

**Por qué se hace así**

- `Código Barras 2`. Mismo paquete, segundo código; no es principal.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<ID_EAN_2>",
  "identifier_type": "EAN",
  "value": "7701021118912",
  "is_primary": false
}
```

**Guardar:** `id` → `<ID_EAN_2>`

---

[← Paso anterior](09-crear-presentacion.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](11-crear-y-asignar-grupos.md)
