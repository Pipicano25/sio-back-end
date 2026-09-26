# Paso 12 de 12 — Verificar el resultado

Ejercicio 2 — Leche NAN 1 Optipro: tres filas del Excel, un solo producto · [← Paso anterior](11-crear-y-asignar-grupos.md) · [Orden del ejercicio](ORDEN.md)

**Objetivo:** Comprobar que cada código lleva a su lata y que el producto quedó elegible.

**Necesita (de pasos anteriores):** `<PRODUCTO>` — pasos [06](06-crear-producto.md)

---

## 1. Consultar el producto con su detalle

```http
GET /api/v1/products/<PRODUCTO>?expand=detail
```

**Permiso que exige la URL:** `perm:product-catalog:products:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:product-catalog:all:read`), `ventas.test` (por `perm:product-catalog:all:read`), `inventario.test` (por `perm:product-catalog:all:read`), `reportes.test` (por `perm:all:all:read`), `consulta.test` (por `perm:all:all:read`)

**Por qué se hace así**

- Debe mostrar tres presentaciones y tres códigos, cada uno ligado a su presentación.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "canonical_name": "NAN 1 Optipro leche en polvo",
  "completeness": {
    "is_complete": true,
    "issues": [],
    "missing_attribute_definition_ids": [],
    "out_of_classification_value_ids": []
  },
  "eligible_for_adoption": true,
  "detail": {
    "presentations": [
      {
        "code": "LATA_400G",
        "base_quantity": "400.00000000"
      },
      {
        "code": "LATA_900G",
        "base_quantity": "900.00000000"
      },
      {
        "code": "LATA_1100G",
        "base_quantity": "1100.00000000"
      }
    ],
    "identifiers": [
      {
        "value": "7501059227453",
        "global_product_presentation_id": "<PRES_LATA_400G>"
      },
      {
        "value": "7501059227644",
        "global_product_presentation_id": "<PRES_LATA_900G>"
      },
      {
        "value": "7501059279124",
        "global_product_presentation_id": "<PRES_LATA_1100G>"
      }
    ]
  }
}
```

## 2. Escanear el código de la lata de 900 g

```http
GET /api/v1/products/by-identifier/7501059227644
```

**Permiso que exige la URL:** `perm:product-catalog:products:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:product-catalog:all:read`), `ventas.test` (por `perm:product-catalog:all:read`), `inventario.test` (por `perm:product-catalog:all:read`), `reportes.test` (por `perm:all:all:read`), `consulta.test` (por `perm:all:all:read`)

**Por qué se hace así**

- Devuelve el producto y la presentación `LATA_900G` con `base_quantity: 900`.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "product": {
    "canonical_name": "NAN 1 Optipro leche en polvo"
  },
  "presentation": {
    "code": "LATA_900G",
    "base_quantity": "900.00000000"
  },
  "is_current": true
}
```

## 3. Listar las fórmulas infantiles de etapa 1

```http
GET /api/v1/products?attribute_filters=FORMULA_INFANTIL:true&attribute_filters=ETAPA_FORMULA:1
```

**Permiso que exige la URL:** `perm:product-catalog:products:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:product-catalog:all:read`), `ventas.test` (por `perm:product-catalog:all:read`), `inventario.test` (por `perm:product-catalog:all:read`), `reportes.test` (por `perm:all:all:read`), `consulta.test` (por `perm:all:all:read`)

**Por qué se hace así**

- En `BOOLEAN` el filtro usa `true` o `false`; en `INTEGER`, el número.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "canonical_name": "NAN 1 Optipro leche en polvo"
    }
  ],
  "total_records": 1
}
```

---

[← Paso anterior](11-crear-y-asignar-grupos.md) · [Orden del ejercicio](ORDEN.md)
