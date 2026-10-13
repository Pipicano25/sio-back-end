# Paso 01 de 08 — Registrar las ventas

Ejercicio 4 — Ventas con precio por presentación (lista indicada y predeterminada), rechazos, costo FIFO y margen · [Orden del ejercicio](ORDEN.md)

---

## 1. Registrar la venta V1 en borrador

Paso `V-01.V1` · usuario **`ventas.test`** · ítems de la FASE 10: 13

```http
POST http://127.0.0.1:8108/api/v1/companies/<EMPRESA_A>/sales
```

```json
{
  "branch_id": "<SUCURSAL_A1>",
  "company_customer_id": "<CLIENTE>",
  "lines": [
    {
      "company_product_id": "<PRODUCTO_EMPRESA_A>",
      "company_product_presentation_id": "<PRESENTACION_CAJA_EMPRESA_A>",
      "price_list_id": "<LISTA_MAYORISTA>",
      "quantity": "1"
    }
  ]
}
```

**Permiso que exige la URL:** `perm:sales:sales:create` + `perm:sales:sale_details:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `ventas.test` (por `perm:sales:all:create`), `supervisor.test` (por `perm:all:all:create`)

**Por qué se hace así**

- Lista indicada MAYORISTA: precio de la caja 16 000

**Respuesta esperada:** `201`

**Guardar:** `id` → `<VENTA_1>`, `version` → `<VENTA_1_VERSION>`

**Auditoría que deja:** `CREATE_SALE` (sales)

## 2. Registrar la venta V2 en borrador

Paso `V-01.V2` · usuario **`ventas.test`** · ítems de la FASE 10: 13

```http
POST http://127.0.0.1:8108/api/v1/companies/<EMPRESA_A>/sales
```

```json
{
  "branch_id": "<SUCURSAL_A1>",
  "company_customer_id": "<CLIENTE>",
  "lines": [
    {
      "company_product_id": "<PRODUCTO_EMPRESA_A>",
      "company_product_presentation_id": "<PRESENTACION_BASE_EMPRESA_A>",
      "quantity": "20"
    }
  ]
}
```

**Permiso que exige la URL:** `perm:sales:sales:create` + `perm:sales:sale_details:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `ventas.test` (por `perm:sales:all:create`), `supervisor.test` (por `perm:all:all:create`)

**Por qué se hace así**

- Sin lista: se aplica la predeterminada GENERAL, 1 500 la unidad

**Respuesta esperada:** `201`

**Guardar:** `id` → `<VENTA_2>`, `version` → `<VENTA_2_VERSION>`

**Auditoría que deja:** `CREATE_SALE` (sales)

## 3. Registrar la venta V3 en borrador

Paso `V-01.V3` · usuario **`ventas.test`** · ítems de la FASE 10: 13

```http
POST http://127.0.0.1:8108/api/v1/companies/<EMPRESA_A>/sales
```

```json
{
  "branch_id": "<SUCURSAL_A1>",
  "company_customer_id": "<CLIENTE>",
  "lines": [
    {
      "company_product_id": "<PRODUCTO_EMPRESA_B>",
      "company_product_presentation_id": "<PRESENTACION_BASE_EMPRESA_B>",
      "quantity": "4"
    }
  ]
}
```

**Permiso que exige la URL:** `perm:sales:sales:create` + `perm:sales:sale_details:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `ventas.test` (por `perm:sales:all:create`), `supervisor.test` (por `perm:all:all:create`)

**Por qué se hace así**

- Producto B: precio de su unidad en la lista predeterminada GENERAL, 7 000

**Respuesta esperada:** `201`

**Guardar:** `id` → `<VENTA_3>`, `version` → `<VENTA_3_VERSION>`

**Auditoría que deja:** `CREATE_SALE` (sales)

## 4. Registrar la venta V4 en borrador

Paso `V-01.V4` · usuario **`ventas.test`** · ítems de la FASE 10: 13

```http
POST http://127.0.0.1:8108/api/v1/companies/<EMPRESA_A>/sales
```

```json
{
  "branch_id": "<SUCURSAL_A1>",
  "company_customer_id": "<CLIENTE>",
  "lines": [
    {
      "company_product_id": "<PRODUCTO_EMPRESA_A>",
      "company_product_presentation_id": "<PRESENTACION_BASE_EMPRESA_A>",
      "quantity": "100"
    }
  ]
}
```

**Permiso que exige la URL:** `perm:sales:sales:create` + `perm:sales:sale_details:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `ventas.test` (por `perm:sales:all:create`), `supervisor.test` (por `perm:all:all:create`)

**Por qué se hace así**

- 100 unidades (más de las existentes)

**Respuesta esperada:** `201`

**Guardar:** `id` → `<VENTA_4>`, `version` → `<VENTA_4_VERSION>`

**Auditoría que deja:** `CREATE_SALE` (sales)

## 5. Registrar la venta V5 en borrador

Paso `V-01.V5` · usuario **`ventas.test`** · ítems de la FASE 10: 13

```http
POST http://127.0.0.1:8108/api/v1/companies/<EMPRESA_A>/sales
```

```json
{
  "branch_id": "<SUCURSAL_A1>",
  "company_customer_id": "<CLIENTE>",
  "lines": [
    {
      "company_product_id": "<PRODUCTO_EMPRESA_A>",
      "company_product_presentation_id": "<PRESENTACION_BASE_EMPRESA_A>",
      "quantity": "1"
    }
  ]
}
```

**Permiso que exige la URL:** `perm:sales:sales:create` + `perm:sales:sale_details:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `ventas.test` (por `perm:sales:all:create`), `supervisor.test` (por `perm:all:all:create`)

**Por qué se hace así**

- Lista predeterminada; su precio cambiará antes de confirmar

**Respuesta esperada:** `201`

**Guardar:** `id` → `<VENTA_5>`, `version` → `<VENTA_5_VERSION>`

**Auditoría que deja:** `CREATE_SALE` (sales)

## 6. Registrar la venta V6 en borrador

Paso `V-01.V6` · usuario **`ventas.test`** · ítems de la FASE 10: 13

```http
POST http://127.0.0.1:8108/api/v1/companies/<EMPRESA_A>/sales
```

```json
{
  "branch_id": "<SUCURSAL_A1>",
  "company_customer_id": "<CLIENTE>",
  "lines": [
    {
      "company_product_id": "<PRODUCTO_EMPRESA_A>",
      "company_product_presentation_id": "<PRESENTACION_BASE_EMPRESA_A>",
      "quantity": "1"
    }
  ]
}
```

**Permiso que exige la URL:** `perm:sales:sales:create` + `perm:sales:sale_details:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `ventas.test` (por `perm:sales:all:create`), `supervisor.test` (por `perm:all:all:create`)

**Por qué se hace así**

- Borrador que se anulará

**Respuesta esperada:** `201`

**Guardar:** `id` → `<VENTA_6>`, `version` → `<VENTA_6_VERSION>`

**Auditoría que deja:** `CREATE_SALE` (sales)

## 7. Registrar la venta V7 en borrador

Paso `V-01.V7` · usuario **`ventas.test`** · ítems de la FASE 10: 13

```http
POST http://127.0.0.1:8108/api/v1/companies/<EMPRESA_A>/sales
```

```json
{
  "branch_id": "<SUCURSAL_A1>",
  "company_customer_id": "<CLIENTE>",
  "lines": [
    {
      "company_product_id": "<PRODUCTO_EMPRESA_B>",
      "company_product_presentation_id": "<PRESENTACION_BASE_EMPRESA_B>",
      "quantity": "1"
    }
  ]
}
```

**Permiso que exige la URL:** `perm:sales:sales:create` + `perm:sales:sale_details:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `ventas.test` (por `perm:sales:all:create`), `supervisor.test` (por `perm:all:all:create`)

**Por qué se hace así**

- Producto B; se inactivará antes de confirmar

**Respuesta esperada:** `201`

**Guardar:** `id` → `<VENTA_7>`, `version` → `<VENTA_7_VERSION>`

**Auditoría que deja:** `CREATE_SALE` (sales)
