# Paso 06 de 12 — Crear el producto

Ejercicio 3 — Pañal Winny Gold etapa 6 XXXG, paquete x 30 · [← Paso anterior](05-asociar-atributos-a-la-categoria.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](07-clasificar-producto.md)

**Objetivo:** Registrar el pañal.

**Necesita (de pasos anteriores):** `<MARCA_WINNY>`, `<FABRICANTE_TECNOQUIMICAS>`, `<UND>` — pasos [01](01-consultar-datos-base.md), [02](02-crear-marca.md)

**Deja guardado para los siguientes pasos:** `<PRODUCTO>`

---

## 1. Crear el producto

```http
POST /api/v1/products
```

```json
{
  "product_type": "GOOD",
  "canonical_name": "Winny Gold pañal etapa 6 talla XXXG",
  "global_brand_id": "<MARCA_WINNY>",
  "manufacturer_organization_id": "<FABRICANTE_TECNOQUIMICAS>",
  "base_unit_id": "<UND>"
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `create`

**Por qué se hace así**

- La talla **sí** va en el nombre: un pañal XXXG y uno G son productos distintos (se compran por separado), no presentaciones del mismo producto. Además queda en el atributo para poder filtrar.
- No lleva `PAQUETEX30` (es la presentación) ni `TECNOQUIMICAS` (es el fabricante).
- `description` se omite: es opcional.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<PRODUCTO>",
  "version": 1,
  "status": "ACTIVE",
  "canonical_name": "Winny Gold pañal etapa 6 talla XXXG",
  "global_brand_id": "<MARCA_WINNY>",
  "manufacturer_organization_id": "<FABRICANTE_TECNOQUIMICAS>",
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
