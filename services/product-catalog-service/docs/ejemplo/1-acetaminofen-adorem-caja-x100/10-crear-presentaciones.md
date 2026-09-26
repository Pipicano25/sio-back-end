# Paso 10 de 13 — Crear las presentaciones

Ejercicio 1 — Acetaminofén Adorem 500 mg, caja x 100 · [← Paso anterior](09-registrar-valores-de-atributos.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](11-registrar-codigos-de-barras.md)

**Objetivo:** Registrar cómo se vende: por tableta suelta y por caja de 100.

**Necesita (de pasos anteriores):** `<PRODUCTO>`, `<BOX>` — pasos [01](01-consultar-datos-base.md), [07](07-crear-producto.md)

**Deja guardado para los siguientes pasos:** `<PRES_TABLETA>`, `<PRES_CAJA_X100>`

---

## 1. Presentación base `TABLETA`

```http
POST /api/v1/products/<PRODUCTO>/presentations
```

```json
{
  "code": "TABLETA",
  "name": "Tableta",
  "base_quantity": 1,
  "display_order": 1,
  "is_base": true
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Todo lo que se agrega **dentro** de un producto (categorías, valores, presentaciones, códigos, grupos, imágenes) exige `update` sobre `products`.

**Por qué se hace así**

- `is_base: true`: es la presentación que equivale a **una** unidad base; por eso `base_quantity` debe ser `1` (otro valor da `422 BASE_QUANTITY_MUST_BE_ONE`).
- Sin `packaging_type_id`: la tableta suelta no tiene empaque propio.
- Permite que las farmacias vendan tabletas sueltas y conviertan entre caja y tableta.
- Solo puede haber **una** presentación base activa por producto (`409 BASE_PRESENTATION_EXISTS`).

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<PRES_TABLETA>",
  "code": "TABLETA",
  "name": "Tableta",
  "packaging_type_id": null,
  "base_quantity": "1.00000000",
  "is_base": true,
  "status": "ACTIVE",
  "eligible_for_adoption": true
}
```

**Guardar:** `id` → `<PRES_TABLETA>`

## 2. Presentación `CAJA_X100`

```http
POST /api/v1/products/<PRODUCTO>/presentations
```

```json
{
  "code": "CAJA_X100",
  "name": "Caja x 100 tabletas",
  "packaging_type_id": "<BOX>",
  "base_quantity": 100,
  "display_order": 2,
  "is_base": false
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Todo lo que se agrega **dentro** de un producto (categorías, valores, presentaciones, códigos, grupos, imágenes) exige `update` sobre `products`.

**Por qué se hace así**

- `base_quantity: 100` es el **factor de conversión**: una caja = 100 tabletas (`Contenido Interno = 100` en el Excel).
- `packaging_type_id: BOX` porque `Unidad Medida = CAJA`.
- No se usa `content_quantity`: ese campo es para contenido medido en otra unidad (p. ej. un frasco de 120 mL).
- `code` es único dentro del producto y no se puede cambiar ni reutilizar.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<PRES_CAJA_X100>",
  "code": "CAJA_X100",
  "name": "Caja x 100 tabletas",
  "packaging_type_id": "<BOX>",
  "base_quantity": "100.00000000",
  "is_base": false,
  "status": "ACTIVE",
  "eligible_for_adoption": true
}
```

**Guardar:** `id` → `<PRES_CAJA_X100>`

---

[← Paso anterior](09-registrar-valores-de-atributos.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](11-registrar-codigos-de-barras.md)
