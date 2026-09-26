# Paso 06 de 12 — Crear el producto (uno solo para las tres filas)

Ejercicio 2 — Leche NAN 1 Optipro: tres filas del Excel, un solo producto · [← Paso anterior](05-asociar-atributos-a-la-categoria.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](07-clasificar-producto.md)

**Objetivo:** Registrar un único producto con el gramo como unidad base.

**Necesita (de pasos anteriores):** `<MARCA_NAN>`, `<FABRICANTE_NESTLE>`, `<G>` — pasos [01](01-consultar-datos-base.md), [02](02-crear-marca.md)

**Deja guardado para los siguientes pasos:** `<PRODUCTO>`

---

## 1. Crear el producto

```http
POST /api/v1/products
```

```json
{
  "product_type": "GOOD",
  "canonical_name": "NAN 1 Optipro leche en polvo",
  "description": "Fórmula láctea infantil en polvo, etapa 1.",
  "global_brand_id": "<MARCA_NAN>",
  "manufacturer_organization_id": "<FABRICANTE_NESTLE>",
  "base_unit_id": "<G>"
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `create`

**Por qué se hace así**

- **Un solo producto**: lo que cambia entre las tres filas es el tamaño de la lata, que es una presentación.
- `canonical_name` no lleva el tamaño (`LATAX400G`) ni la referencia `RF12495528`.
- `base_unit_id: G`: con gramos las tres latas quedan en la misma unidad y se pueden convertir entre sí. Con `UND` una lata de 400 g y una de 900 g valdrían "1" cada una, lo que no permite comparar ni convertir.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<PRODUCTO>",
  "version": 1,
  "status": "ACTIVE",
  "canonical_name": "NAN 1 Optipro leche en polvo",
  "global_brand_id": "<MARCA_NAN>",
  "manufacturer_organization_id": "<FABRICANTE_NESTLE>",
  "base_unit_id": "<G>",
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

> Si alguien vuelve a crear el mismo nombre con la misma marca, el servicio lo acepta pero devuelve la advertencia `POSSIBLE_DUPLICATE` en `warnings`. Es la señal de que se está duplicando una fila del Excel.

---

[← Paso anterior](05-asociar-atributos-a-la-categoria.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](07-clasificar-producto.md)
