# Paso 06 de 06 — Crear las listas de precios

Ejercicio 2 — Relación comercial y precios: proveedor, cliente, productos, adopción, presentaciones y listas · [Orden del ejercicio](ORDEN.md)

---

## 1. Crear la lista de precios GENERAL

Paso `C-12.lista_general` · usuario **`admin.test`** · ítems de la FASE 10: 8

```http
POST http://127.0.0.1:8106/api/v1/companies/<EMPRESA_A>/price-lists
```

```json
{
  "code": "GENERAL-<RUN_ID>",
  "name": "Lista GENERAL MVP <RUN_ID> (dato ficticio)",
  "currency_code": "COP",
  "is_default": true
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:price_lists:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:commercial-relationship:all:create`)

**Por qué se hace así**

- GENERAL es la predeterminada: se aplica cuando la venta no indica lista.

**Respuesta esperada:** `201`

**Guardar:** `id` → `<LISTA_GENERAL>`

**Auditoría que deja:** `CREATE_PRICE_LIST` (commercial-relationship)

## 2. Crear la lista de precios MAYORISTA

Paso `C-12.lista_mayorista` · usuario **`admin.test`** · ítems de la FASE 10: 8

```http
POST http://127.0.0.1:8106/api/v1/companies/<EMPRESA_A>/price-lists
```

```json
{
  "code": "MAYORISTA-<RUN_ID>",
  "name": "Lista MAYORISTA MVP <RUN_ID> (dato ficticio)",
  "currency_code": "COP",
  "is_default": false
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:price_lists:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:commercial-relationship:all:create`)

**Por qué se hace así**

- MAYORISTA solo se aplica si la línea la indica.

**Respuesta esperada:** `201`

**Guardar:** `id` → `<LISTA_MAYORISTA>`

**Auditoría que deja:** `CREATE_PRICE_LIST` (commercial-relationship)

## 3. Precio de la unidad del producto A en GENERAL

Paso `C-12.item_general` · usuario **`admin.test`** · ítems de la FASE 10: 8

```http
POST http://127.0.0.1:8106/api/v1/companies/<EMPRESA_A>/price-list-items
```

```json
{
  "price_list_id": "<LISTA_GENERAL>",
  "company_product_id": "<PRODUCTO_EMPRESA_A>",
  "company_product_presentation_id": "<PRESENTACION_BASE_EMPRESA_A>",
  "unit_price": "1500.00"
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:price_list_items:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:commercial-relationship:all:create`)

**Por qué se hace así**

- Cada presentación vendible tiene su precio explícito (spec 019); no hay precios generales por producto.

**Respuesta esperada:** `201`

**Guardar:** `id` → `<ITEM_GENERAL>`, `version` → `<ITEM_GENERAL_VERSION>`

**Auditoría que deja:** `CREATE_PRICE_LIST_ITEM` (commercial-relationship)

## 4. Precio de la unidad del producto B en GENERAL

Paso `C-12.item_b` · usuario **`admin.test`** · ítems de la FASE 10: 8

```http
POST http://127.0.0.1:8106/api/v1/companies/<EMPRESA_A>/price-list-items
```

```json
{
  "price_list_id": "<LISTA_GENERAL>",
  "company_product_id": "<PRODUCTO_EMPRESA_B>",
  "company_product_presentation_id": "<PRESENTACION_BASE_EMPRESA_B>",
  "unit_price": "7000.00"
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:price_list_items:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:commercial-relationship:all:create`)

**Respuesta esperada:** `201`

**Guardar:** `id` → `<ITEM_B>`

**Auditoría que deja:** `CREATE_PRICE_LIST_ITEM` (commercial-relationship)

## 5. Precio de la caja del producto A en MAYORISTA

Paso `C-12.item_mayorista` · usuario **`admin.test`** · ítems de la FASE 10: 8

```http
POST http://127.0.0.1:8106/api/v1/companies/<EMPRESA_A>/price-list-items
```

```json
{
  "price_list_id": "<LISTA_MAYORISTA>",
  "company_product_id": "<PRODUCTO_EMPRESA_A>",
  "company_product_presentation_id": "<PRESENTACION_CAJA_EMPRESA_A>",
  "unit_price": "16000.00"
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:price_list_items:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:commercial-relationship:all:create`)

**Respuesta esperada:** `201`

**Guardar:** `id` → `<ITEM_MAYORISTA>`

**Auditoría que deja:** `CREATE_PRICE_LIST_ITEM` (commercial-relationship)

## 6. Configurar la tasa de impuesto de compra de los productos A y B (0 %)

Paso `C-12.tasas` · usuario **`admin.test`** · ítems de la FASE 10: 8

```http
POST http://127.0.0.1:8106/api/v1/companies/<EMPRESA_A>/company-products/purchase-taxes/batch
```

```json
{
  "items": [
    {
      "company_product_id": "<PRODUCTO_EMPRESA_A>",
      "version": "<PRODUCTO_EMPRESA_A_VERSION>",
      "purchase_tax_percentage": "0"
    },
    {
      "company_product_id": "<PRODUCTO_EMPRESA_B>",
      "version": "<PRODUCTO_EMPRESA_B_VERSION>",
      "purchase_tax_percentage": "0"
    }
  ]
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_product_purchase_taxes:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:commercial-relationship:all:update`)

**Por qué se hace así**

- Spec 021: sin tasa la compra no se confirma. 0 % (exento, dato ficticio) conserva exactos los costos y márgenes del escenario; `null` sería «sin configurar».

**Respuesta esperada:** `200`

**Guardar:** `items.0.version` → `<PRODUCTO_EMPRESA_A_VERSION>`, `items.1.version` → `<PRODUCTO_EMPRESA_B_VERSION>`

**Auditoría que deja:** `UPDATE_COMPANY_PRODUCT_PURCHASE_TAX` (commercial-relationship), `UPDATE_COMPANY_PRODUCT_PURCHASE_TAX` (commercial-relationship)

## 7. Crear la lista de precios AUTOMATICA

Paso `C-12.lista_automatica` · usuario **`admin.test`** · ítems de la FASE 10: 8

```http
POST http://127.0.0.1:8106/api/v1/companies/<EMPRESA_A>/price-lists
```

```json
{
  "code": "AUTOMATICA-<RUN_ID>",
  "name": "Lista AUTOMATICA MVP <RUN_ID> (dato ficticio)",
  "currency_code": "COP",
  "is_default": false
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:price_lists:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:commercial-relationship:all:create`)

**Por qué se hace así**

- Spec 021: solo esta lista tiene política; GENERAL y MAYORISTA conservan sus precios manuales y las ventas no la usan.

**Respuesta esperada:** `201`

**Guardar:** `id` → `<LISTA_AUTOMATICA>`

**Auditoría que deja:** `CREATE_PRICE_LIST` (commercial-relationship)

## 8. Crear la política de ganancia (30 %) con las presentaciones que se compran

Paso `C-12.politica` · usuario **`admin.test`** · ítems de la FASE 10: 8

```http
POST http://127.0.0.1:8106/api/v1/companies/<EMPRESA_A>/price-lists/<LISTA_AUTOMATICA>/pricing-policies
```

```json
{
  "name": "MVP <RUN_ID> (dato ficticio)",
  "markup_percentage": "30",
  "company_product_presentation_ids": [
    "<PRESENTACION_CAJA_EMPRESA_A>",
    "<PRESENTACION_BASE_EMPRESA_A>",
    "<PRESENTACION_BASE_EMPRESA_B>"
  ]
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:pricing_policies:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:commercial-relationship:all:create`)

**Por qué se hace así**

- La política no cambia precios: rige desde la siguiente recepción física. Spec 021 (FR-021-35): una compra solo se confirma si cada presentación tiene política de ganancia aplicable, por eso incluye las tres presentaciones que se compran.

**Respuesta esperada:** `201`

**Guardar:** `id` → `<POLITICA>`

**Auditoría que deja:** `CREATE_PRICING_POLICY` (commercial-relationship)
