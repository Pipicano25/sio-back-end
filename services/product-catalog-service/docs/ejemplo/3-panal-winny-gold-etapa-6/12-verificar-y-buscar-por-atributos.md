# Paso 12 de 12 — Verificar y buscar por atributos

Ejercicio 3 — Pañal Winny Gold etapa 6 XXXG, paquete x 30 · [← Paso anterior](11-crear-y-asignar-grupos.md) · [Orden del ejercicio](ORDEN.md)

**Objetivo:** Comprobar el producto y usar los filtros por atributo.

**Necesita (de pasos anteriores):** `<PRODUCTO>`, `<CAT_PANALES_BEBE>` — pasos [03](03-crear-categorias.md), [06](06-crear-producto.md)

---

## 1. Consultar el producto

```http
GET /api/v1/products/<PRODUCTO>
```

**Permiso que exige la URL:** `perm:product-catalog:products:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:product-catalog:all:read`), `ventas.test` (por `perm:product-catalog:all:read`), `inventario.test` (por `perm:product-catalog:all:read`), `reportes.test` (por `perm:product-catalog:products:read`), `consulta.test` (por `perm:product-catalog:products:read`)

**Por qué se hace así**

- Sin `expand` la respuesta es más liviana: basta para ver completitud y elegibilidad.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "canonical_name": "Winny Gold pañal etapa 6 talla XXXG",
  "completeness": {
    "is_complete": true,
    "issues": [],
    "missing_attribute_definition_ids": [],
    "out_of_classification_value_ids": []
  },
  "eligible_for_adoption": true
}
```

## 2. Buscar pañales talla XXXG

```http
GET /api/v1/products?attribute_filters=TALLA_PANAL:XXXG
```

**Permiso que exige la URL:** `perm:product-catalog:products:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:product-catalog:all:read`), `ventas.test` (por `perm:product-catalog:all:read`), `inventario.test` (por `perm:product-catalog:all:read`), `reportes.test` (por `perm:product-catalog:products:read`), `consulta.test` (por `perm:product-catalog:products:read`)

**Por qué se hace así**

- En atributos `OPTION` el filtro usa el **código** de la opción (`XXXG`), no su `id`.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "canonical_name": "Winny Gold pañal etapa 6 talla XXXG"
    }
  ],
  "total_records": 1
}
```

## 3. Buscar pañales talla XXXG de etapa 6 en la categoría

```http
GET /api/v1/products?category_id=<CAT_PANALES_BEBE>&attribute_filters=TALLA_PANAL:XXXG&attribute_filters=ETAPA_PANAL:6
```

**Permiso que exige la URL:** `perm:product-catalog:products:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:product-catalog:all:read`), `ventas.test` (por `perm:product-catalog:all:read`), `inventario.test` (por `perm:product-catalog:all:read`), `reportes.test` (por `perm:product-catalog:products:read`), `consulta.test` (por `perm:product-catalog:products:read`)

**Por qué se hace así**

- Los filtros se combinan (todos deben cumplirse). `attribute_filters` se repite una vez por atributo.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "canonical_name": "Winny Gold pañal etapa 6 talla XXXG"
    }
  ],
  "total_records": 1
}
```

## 4. Error esperado: filtrar por un atributo no filtrable

```http
GET /api/v1/products?attribute_filters=NO_EXISTE:1
```

**Permiso que exige la URL:** `perm:product-catalog:products:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:product-catalog:all:read`), `ventas.test` (por `perm:product-catalog:all:read`), `inventario.test` (por `perm:product-catalog:all:read`), `reportes.test` (por `perm:product-catalog:products:read`), `consulta.test` (por `perm:product-catalog:products:read`)

**Por qué se hace así**

- Si el atributo no existe o no es filtrable en ninguna categoría, responde `422 ATTRIBUTE_NOT_FILTERABLE`.

**Respuesta esperada (error) — `422 Unprocessable Content`** (abreviada)

```json
{
  "status": 422,
  "code": "PRODUCT_CATALOG.ATTRIBUTE_NOT_FILTERABLE",
  "detail": "El atributo NO_EXISTE no es filtrable en ninguna categoría vigente."
}
```

---

[← Paso anterior](11-crear-y-asignar-grupos.md) · [Orden del ejercicio](ORDEN.md)
