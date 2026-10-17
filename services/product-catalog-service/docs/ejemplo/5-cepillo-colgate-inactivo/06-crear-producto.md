# Paso 06 de 14 — Crear el producto

Ejercicio 5 — Cepillo Colgate infantil pack x 2 (producto inactivo) · [← Paso anterior](05-asociar-atributos-a-la-categoria.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](07-clasificar-y-registrar-atributos.md)

**Objetivo:** Registrar el cepillo **activo**, aunque el Excel diga `I`.

**Necesita (de pasos anteriores):** `<MARCA_COLGATE>`, `<FABRICANTE_COLGATE>`, `<UND>` — pasos [01](01-consultar-datos-base.md), [02](02-crear-marca.md)

**Deja guardado para los siguientes pasos:** `<PRODUCTO>`

---

## 1. Crear el producto

```http
POST /api/v1/products
```

```json
{
  "product_type": "GOOD",
  "canonical_name": "Colgate cepillo dental infantil 2 a 5 años extra suave niña",
  "global_brand_id": "<MARCA_COLGATE>",
  "manufacturer_organization_id": "<FABRICANTE_COLGATE>",
  "base_unit_id": "<UND>"
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `create`

**Por qué se hace así**

- El cuerpo **no admite** `status`: todo producto nace `ACTIVE`. El estado se cambia con acciones (`/deactivate`, `/reactivate`), no con un campo.
- Se inactiva **al final** porque sobre un producto inactivo no se pueden agregar categorías, presentaciones, atributos ni grupos (`422 PRODUCT_INACTIVE`). Se carga completo primero para que la información quede íntegra si algún día se reactiva.
- "NIÑA" se conserva en el nombre: el diseño niña y el diseño niño son productos distintos con códigos distintos.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<PRODUCTO>",
  "version": 1,
  "status": "ACTIVE",
  "canonical_name": "Colgate cepillo dental infantil 2 a 5 años extra suave niña",
  "global_brand_id": "<MARCA_COLGATE>",
  "manufacturer_organization_id": "<FABRICANTE_COLGATE>",
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

[← Paso anterior](05-asociar-atributos-a-la-categoria.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](07-clasificar-y-registrar-atributos.md)
