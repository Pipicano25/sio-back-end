# Paso 06 de 11 — Crear el producto (sin marca)

Ejercicio 4 — Aguja hipodérmica 18G x 1½" Rymco, caja x 100 · [← Paso anterior](05-asociar-atributos-a-la-categoria.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](07-clasificar-producto.md)

**Objetivo:** Registrar la aguja.

**Necesita (de pasos anteriores):** `<FABRICANTE_RYMCO>`, `<UND>` — pasos [01](01-consultar-datos-base.md)

**Deja guardado para los siguientes pasos:** `<PRODUCTO>`

---

## 1. Crear el producto

```http
POST /api/v1/products
```

```json
{
  "product_type": "GOOD",
  "canonical_name": "Aguja hipodérmica 18G x 1 1/2 pulgadas",
  "description": "Aguja hipodérmica estéril de un solo uso.",
  "manufacturer_organization_id": "<FABRICANTE_RYMCO>",
  "base_unit_id": "<UND>"
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `create`

**Por qué se hace así**

- No se envía `global_brand_id`: el producto no tiene marca comercial propia. Inventar una marca "RYMCO" mezclaría fabricante y marca.
- `RFZC18B` no va en el nombre: se registra como identificador `OTHER` (paso 9).

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<PRODUCTO>",
  "version": 1,
  "status": "ACTIVE",
  "canonical_name": "Aguja hipodérmica 18G x 1 1/2 pulgadas",
  "global_brand_id": null,
  "manufacturer_organization_id": "<FABRICANTE_RYMCO>",
  "base_unit_id": "<UND>",
  "completeness": {
    "is_complete": false,
    "issues": [
      "NO_ACTIVE_CATEGORY",
      "NO_ACTIVE_PRESENTATION"
    ],
    "missing_attribute_definition_ids": [],
    "out_of_classification_value_ids": []
  },
  "eligible_for_adoption": false
}
```

**Guardar:** `id` → `<PRODUCTO>`

---

[← Paso anterior](05-asociar-atributos-a-la-categoria.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](07-clasificar-producto.md)
