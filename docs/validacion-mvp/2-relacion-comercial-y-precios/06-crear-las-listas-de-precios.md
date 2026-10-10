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

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)

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

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)

**Por qué se hace así**

- MAYORISTA solo se aplica si la línea la indica.

**Respuesta esperada:** `201`

**Guardar:** `id` → `<LISTA_MAYORISTA>`

**Auditoría que deja:** `CREATE_PRICE_LIST` (commercial-relationship)

## 3. Precio por unidad del producto A en GENERAL

Paso `C-12.item_general` · usuario **`admin.test`** · ítems de la FASE 10: 8

```http
POST http://127.0.0.1:8106/api/v1/companies/<EMPRESA_A>/price-list-items
```

```json
{
  "price_list_id": "<LISTA_GENERAL>",
  "company_product_id": "<PRODUCTO_EMPRESA_A>",
  "unit_price": "1500.00"
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:price_list_items:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)

**Respuesta esperada:** `201`

**Guardar:** `id` → `<ITEM_GENERAL>`, `version` → `<ITEM_GENERAL_VERSION>`

**Auditoría que deja:** `CREATE_PRICE_LIST_ITEM` (commercial-relationship)

## 4. Precio de la caja del producto A en MAYORISTA

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

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)

**Respuesta esperada:** `201`

**Guardar:** `id` → `<ITEM_MAYORISTA>`

**Auditoría que deja:** `CREATE_PRICE_LIST_ITEM` (commercial-relationship)
