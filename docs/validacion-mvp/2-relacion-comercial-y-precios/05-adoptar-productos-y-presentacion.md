# Paso 05 de 06 — Adoptar productos y presentación

Ejercicio 2 — Relación comercial y precios: proveedor, cliente, productos, adopción, presentaciones y listas · [Orden del ejercicio](ORDEN.md)

---

## 1. Adoptar el producto A en la empresa A

Paso `C-11.producto_a` · usuario **`admin.test`** · ítems de la FASE 10: 6, 8

```http
POST http://127.0.0.1:8106/api/v1/companies/<EMPRESA_A>/company-products
```

```json
{
  "global_product_id": "<PRODUCTO_A>",
  "internal_code": "MVP-A-<RUN_ID>",
  "display_name": "Producto A MVP <RUN_ID> (dato ficticio)",
  "currency_code": "COP",
  "sale_price": "1600.00",
  "inventory_control_enabled": true
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_products:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)

**Por qué se hace así**

- La adopción registra el primer uso del producto global en Product Catalog con la identidad técnica de Commercial Relationship; `sale_price` es el precio simple del producto.

**Respuesta esperada:** `201`

**Guardar:** `id` → `<PRODUCTO_EMPRESA_A>`, `version` → `<PRODUCTO_EMPRESA_A_VERSION>`

**Auditoría que deja:** `ADOPT_COMPANY_PRODUCT` (commercial-relationship), `REGISTER_PRODUCT_FIRST_USE` (product-catalog)

## 2. Adoptar el producto B en la empresa A

Paso `C-11.producto_b` · usuario **`admin.test`** · ítems de la FASE 10: 6, 8

```http
POST http://127.0.0.1:8106/api/v1/companies/<EMPRESA_A>/company-products
```

```json
{
  "global_product_id": "<PRODUCTO_B>",
  "internal_code": "MVP-B-<RUN_ID>",
  "display_name": "Producto B MVP <RUN_ID> (dato ficticio)",
  "currency_code": "COP",
  "sale_price": "7000.00",
  "inventory_control_enabled": true
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_products:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)

**Por qué se hace así**

- La adopción registra el primer uso del producto global en Product Catalog con la identidad técnica de Commercial Relationship; `sale_price` es el precio simple del producto.

**Respuesta esperada:** `201`

**Guardar:** `id` → `<PRODUCTO_EMPRESA_B>`, `version` → `<PRODUCTO_EMPRESA_B_VERSION>`

**Auditoría que deja:** `ADOPT_COMPANY_PRODUCT` (commercial-relationship), `REGISTER_PRODUCT_FIRST_USE` (product-catalog)

## 3. Adoptar la presentación "Caja × 12" del producto A

Paso `C-11.caja_a` · usuario **`admin.test`** · ítems de la FASE 10: 7

```http
POST http://127.0.0.1:8106/api/v1/companies/<EMPRESA_A>/company-product-presentations
```

```json
{
  "company_product_id": "<PRODUCTO_EMPRESA_A>",
  "global_product_presentation_id": "<PRESENTACION_CAJA_A>",
  "sku": "SKU-CJ12-<RUN_ID>"
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_product_presentations:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)

**Por qué se hace así**

- La adopción de la presentación registra también su primer uso (la presentación queda bloqueada para cambios materiales).

**Respuesta esperada:** `201`

**Guardar:** `id` → `<PRESENTACION_CAJA_EMPRESA_A>`

**Auditoría que deja:** `CREATE_COMPANY_PRODUCT_PRESENTATION` (commercial-relationship), `REGISTER_PRODUCT_FIRST_USE` (product-catalog)
