# Paso 07 de 13 — Crear el producto

Ejercicio 1 — Acetaminofén Adorem 500 mg, caja x 100 · [← Paso anterior](06-asociar-atributos-a-la-categoria.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](08-clasificar-producto.md)

**Objetivo:** Registrar el producto global con sus datos mínimos, marca y fabricante.

**Necesita (de pasos anteriores):** `<MARCA_ADOREM>`, `<FABRICANTE_SIEGFRIED>`, `<UND>` — pasos [01](01-consultar-datos-base.md), [03](03-crear-marca.md)

**Deja guardado para los siguientes pasos:** `<PRODUCTO>`

---

## 1. Crear el producto

```http
POST /api/v1/products
```

```json
{
  "product_type": "GOOD",
  "canonical_name": "Acetaminofén 500 mg tableta",
  "description": "Analgésico y antipirético.",
  "global_brand_id": "<MARCA_ADOREM>",
  "manufacturer_organization_id": "<FABRICANTE_SIEGFRIED>",
  "base_unit_id": "<UND>"
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `create`

**Por qué se hace así**

- `product_type: GOOD` es el único tipo admitido en el MVP (bien físico).
- `canonical_name` describe **el producto**, no la presentación: no lleva "caja x 100" (eso va en la presentación) ni el laboratorio (eso va en el fabricante). Se escribe legible, con tildes.
- `global_brand_id` es la marca creada en el paso 3.
- `manufacturer_organization_id` es el `id` de Siegfried en Party Identity; el catálogo lo valida al recibirlo.
- `base_unit_id: UND`: el producto se cuenta en tabletas. Toda cantidad de las presentaciones se expresa en esta unidad.
- No se envían `Código`, `Referencia`, precios ni stock: el cuerpo rechaza campos desconocidos (`422`).

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<PRODUCTO>",
  "version": 1,
  "status": "ACTIVE",
  "canonical_name": "Acetaminofén 500 mg tableta",
  "global_brand_id": "<MARCA_ADOREM>",
  "manufacturer_organization_id": "<FABRICANTE_SIEGFRIED>",
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
  "eligible_for_adoption": false,
  "warnings": []
}
```

**Guardar:** `id` → `<PRODUCTO>`

---

> La respuesta muestra `is_complete: false` con los faltantes: aún no tiene categoría (`NO_ACTIVE_CATEGORY`) ni presentación (`NO_ACTIVE_PRESENTATION`). Es normal: se completan en los pasos siguientes.

---

[← Paso anterior](06-asociar-atributos-a-la-categoria.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](08-clasificar-producto.md)
