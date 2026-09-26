# Paso 09 de 13 — Registrar los valores de los atributos

Ejercicio 1 — Acetaminofén Adorem 500 mg, caja x 100 · [← Paso anterior](08-clasificar-producto.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](10-crear-presentaciones.md)

**Objetivo:** Dar valor a los tres atributos obligatorios.

**Necesita (de pasos anteriores):** `<PRODUCTO>`, `<ATR_PRINCIPIO_ACTIVO>`, `<ATR_CONCENTRACION_MG>`, `<ATR_FORMA_FARMACEUTICA>`, `<OPC_TABLETA>` — pasos [05](05-crear-atributos.md), [07](07-crear-producto.md)

---

## 1. Principio activo = Acetaminofén

```http
PUT /api/v1/products/<PRODUCTO>/attribute-values/<ATR_PRINCIPIO_ACTIVO>
```

```json
{
  "text_value": "Acetaminofén"
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Todo lo que se agrega **dentro** de un producto (categorías, valores, presentaciones, códigos, grupos, imágenes) exige `update` sobre `products`.

**Por qué se hace así**

- Es `PUT` porque registra **o reemplaza** el valor del atributo en la ruta. La primera vez responde `201`.
- Se envía **un solo** campo de valor, el que corresponde al tipo: `TEXT` → `text_value`.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "attribute_definition_id": "<ATR_PRINCIPIO_ACTIVO>",
  "text_value": "Acetaminofén",
  "version": 1,
  "out_of_classification": false
}
```

## 2. Concentración = 500 mg

```http
PUT /api/v1/products/<PRODUCTO>/attribute-values/<ATR_CONCENTRACION_MG>
```

```json
{
  "decimal_value": 500
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Todo lo que se agrega **dentro** de un producto (categorías, valores, presentaciones, códigos, grupos, imágenes) exige `update` sobre `products`.

**Por qué se hace así**

- `DECIMAL` → `decimal_value`. Se envía solo el número; la unidad (mg) ya la fija la definición.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "attribute_definition_id": "<ATR_CONCENTRACION_MG>",
  "decimal_value": "500.00000000",
  "version": 1
}
```

## 3. Forma farmacéutica = Tableta

```http
PUT /api/v1/products/<PRODUCTO>/attribute-values/<ATR_FORMA_FARMACEUTICA>
```

```json
{
  "option_id": "<OPC_TABLETA>"
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Todo lo que se agrega **dentro** de un producto (categorías, valores, presentaciones, códigos, grupos, imágenes) exige `update` sobre `products`.

**Por qué se hace así**

- `OPTION` → `option_id`, el `id` de la opción (no su código ni su nombre).
- Si la opción es de otro atributo o está inactiva responde `422 OPTION_NOT_IN_DEFINITION`.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "attribute_definition_id": "<ATR_FORMA_FARMACEUTICA>",
  "option_id": "<OPC_TABLETA>",
  "version": 1
}
```

---

> Para **corregir** un valor después se usa el mismo `PUT` agregando `"version"` con la versión actual del valor.

---

[← Paso anterior](08-clasificar-producto.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](10-crear-presentaciones.md)
