# Paso 09 de 13 — El código `022348` no se registra

Ejercicio 5 — Cepillo Colgate infantil pack x 2 (producto inactivo) · [← Paso anterior](08-crear-presentacion.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](10-agregar-imagen.md)

**Objetivo:** Entender por qué el "código de barras" del Excel no va al catálogo.

**Necesita (de pasos anteriores):** `<PRODUCTO>`, `<PRES_PACK_X2>` — pasos [06](06-crear-producto.md), [08](08-crear-presentacion.md)

`Código Barras 1 = 022348` es **exactamente** la columna `Código` de la misma fila: el sistema anterior copió el código interno en el campo de código de barras.

¿Por qué no registrarlo como `BARCODE` u `OTHER`, que sí lo aceptarían?

- El catálogo es **global** (compartido por todas las empresas). `022348` solo significa algo dentro de la empresa que exportó el Excel; en otra empresa ese número es otro producto.
- `BARCODE` exige unicidad global: el código interno de una empresa bloquearía ese valor para todas.
- Su lugar es `CompanyProduct.internal_code` en Commercial Relationship Service, cuando la empresa adopte el producto.

---

## 1. Error esperado: registrarlo como EAN

```http
POST /api/v1/products/<PRODUCTO>/identifiers
```

```json
{
  "identifier_type": "EAN",
  "value": "022348",
  "global_product_presentation_id": "<PRES_PACK_X2>"
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Todo lo que se agrega **dentro** de un producto (categorías, valores, presentaciones, códigos, grupos, imágenes) exige `update` sobre `products`.

**Por qué se hace así**

- Un EAN/GTIN tiene 8, 12, 13 o 14 dígitos. `022348` tiene 6: responde `422 INVALID_GTIN_FORMAT`.
- Este error es **la señal** de que el dato no es un código de barras real.

**Respuesta esperada (error) — `422 Unprocessable Content`** (abreviada)

```json
{
  "status": 422,
  "code": "PRODUCT_CATALOG.INVALID_GTIN_FORMAT",
  "detail": "GTIN, EAN y UPC deben ser numéricos de 8, 12, 13 o 14 dígitos."
}
```

## 2. Confirmar que el producto no tiene identificadores

```http
GET /api/v1/products/<PRODUCTO>/identifiers
```

**Permiso que exige la URL:** `perm:product-catalog:products:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:product-catalog:all:read`), `ventas.test` (por `perm:product-catalog:all:read`), `inventario.test` (por `perm:product-catalog:all:read`), `reportes.test` (por `perm:product-catalog:products:read`), `consulta.test` (por `perm:product-catalog:products:read`)

**Por qué se hace así**

- Un producto **puede estar completo sin códigos de barras**: la completitud no los exige.

**Respuesta esperada — `200 OK`** (abreviada)

```json
[]
```

---

[← Paso anterior](08-crear-presentacion.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](10-agregar-imagen.md)
