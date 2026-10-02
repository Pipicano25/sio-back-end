# Paso 13 de 13 — Verificar el resultado

Ejercicio 1 — Acetaminofén Adorem 500 mg, caja x 100 · [← Paso anterior](12-crear-y-asignar-grupos.md) · [Orden del ejercicio](ORDEN.md)

**Objetivo:** Comprobar que el producto quedó completo, elegible y que se encuentra por código y por atributos.

**Necesita (de pasos anteriores):** `<PRODUCTO>` — pasos [07](07-crear-producto.md)

---

## 1. Consultar el producto con todo su detalle

```http
GET /api/v1/products/<PRODUCTO>?expand=detail
```

**Permiso que exige la URL:** `perm:product-catalog:products:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:product-catalog:all:read`), `ventas.test` (por `perm:product-catalog:all:read`), `inventario.test` (por `perm:product-catalog:all:read`), `reportes.test` (por `perm:product-catalog:products:read`), `consulta.test` (por `perm:product-catalog:products:read`)

**Por qué se hace así**

- `expand=detail` trae en una sola respuesta categorías, presentaciones, códigos, atributos, grupos y activos.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "canonical_name": "Acetaminofén 500 mg tableta",
  "status": "ACTIVE",
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
        "code": "TABLETA",
        "base_quantity": "1.00000000"
      },
      {
        "code": "CAJA_X100",
        "base_quantity": "100.00000000"
      }
    ],
    "identifiers": [
      {
        "value": "7707355052038",
        "is_primary": false
      },
      {
        "value": "7707355056876",
        "is_primary": true
      }
    ]
  }
}
```

## 2. Buscar por el segundo código de barras

```http
GET /api/v1/products/by-identifier/7707355052038
```

**Permiso que exige la URL:** `perm:product-catalog:products:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:product-catalog:all:read`), `ventas.test` (por `perm:product-catalog:all:read`), `inventario.test` (por `perm:product-catalog:all:read`), `reportes.test` (por `perm:product-catalog:products:read`), `consulta.test` (por `perm:product-catalog:products:read`)

**Por qué se hace así**

- Simula el escaneo en caja: devuelve el producto **y la presentación** (la caja x 100).

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "product": {
    "canonical_name": "Acetaminofén 500 mg tableta"
  },
  "presentation": {
    "code": "CAJA_X100",
    "base_quantity": "100.00000000"
  },
  "identifier": {
    "value": "7707355052038"
  },
  "is_current": true
}
```

## 3. Buscar por atributos filtrables

```http
GET /api/v1/products?attribute_filters=FORMA_FARMACEUTICA:TABLETA&attribute_filters=CONCENTRACION_MG:500
```

**Permiso que exige la URL:** `perm:product-catalog:products:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:product-catalog:all:read`), `ventas.test` (por `perm:product-catalog:all:read`), `inventario.test` (por `perm:product-catalog:all:read`), `reportes.test` (por `perm:product-catalog:products:read`), `consulta.test` (por `perm:product-catalog:products:read`)

**Por qué se hace así**

- Solo funciona con atributos marcados `is_filterable: true`. En `OPTION` se filtra por el **código** de la opción.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "canonical_name": "Acetaminofén 500 mg tableta"
    }
  ],
  "total_records": 1
}
```

---

> Resultado esperado: `is_complete: true` y `eligible_for_adoption: true`. Desde este momento una empresa puede adoptar el producto en Commercial Relationship Service.

---

[← Paso anterior](12-crear-y-asignar-grupos.md) · [Orden del ejercicio](ORDEN.md)
