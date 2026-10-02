# Paso 11 de 11 — Verificar el resultado

Ejercicio 4 — Aguja hipodérmica 18G x 1½" Rymco, caja x 100 · [← Paso anterior](10-crear-y-asignar-grupos.md) · [Orden del ejercicio](ORDEN.md)

**Objetivo:** Escanear ambos códigos y buscar por la referencia del fabricante.

---

## 1. Escanear el GTIN-14 (caja)

```http
GET /api/v1/products/by-identifier/27706634002850
```

**Permiso que exige la URL:** `perm:product-catalog:products:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:product-catalog:all:read`), `ventas.test` (por `perm:product-catalog:all:read`), `inventario.test` (por `perm:product-catalog:all:read`), `reportes.test` (por `perm:product-catalog:products:read`), `consulta.test` (por `perm:product-catalog:products:read`)

**Por qué se hace así**

- Devuelve la presentación `CAJA_X100`: se vendió una caja de 100 agujas.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "product": {
    "canonical_name": "Aguja hipodérmica 18G x 1 1/2 pulgadas"
  },
  "presentation": {
    "code": "CAJA_X100",
    "base_quantity": "100.00000000"
  },
  "identifier": {
    "identifier_type": "GTIN"
  }
}
```

## 2. Escanear el EAN-13 (unidad)

```http
GET /api/v1/products/by-identifier/7706634002856
```

**Permiso que exige la URL:** `perm:product-catalog:products:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:product-catalog:all:read`), `ventas.test` (por `perm:product-catalog:all:read`), `inventario.test` (por `perm:product-catalog:all:read`), `reportes.test` (por `perm:product-catalog:products:read`), `consulta.test` (por `perm:product-catalog:products:read`)

**Por qué se hace así**

- Devuelve la presentación `UNIDAD`.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "product": {
    "canonical_name": "Aguja hipodérmica 18G x 1 1/2 pulgadas"
  },
  "presentation": {
    "code": "UNIDAD",
    "base_quantity": "1.00000000"
  },
  "identifier": {
    "identifier_type": "EAN"
  }
}
```

## 3. Buscar por la referencia del fabricante

```http
GET /api/v1/products?identifier=RFZC18B
```

**Permiso que exige la URL:** `perm:product-catalog:products:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:product-catalog:all:read`), `ventas.test` (por `perm:product-catalog:all:read`), `inventario.test` (por `perm:product-catalog:all:read`), `reportes.test` (por `perm:product-catalog:products:read`), `consulta.test` (por `perm:product-catalog:products:read`)

**Por qué se hace así**

- El filtro `identifier` busca en todos los tipos de identificador, incluido `OTHER`.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "canonical_name": "Aguja hipodérmica 18G x 1 1/2 pulgadas",
      "eligible_for_adoption": true
    }
  ],
  "total_records": 1
}
```

---

[← Paso anterior](10-crear-y-asignar-grupos.md) · [Orden del ejercicio](ORDEN.md)
