# Paso 02 de 05 — Registrar las compras

Ejercicio 3 — Compras e inventario: secuencias, compras de contado, confirmación, recepción física (entradas), saldos, kardex y capas · [Orden del ejercicio](ORDEN.md)

---

## 1. Registrar la compra P1 en borrador

Paso `P-01.P1` · usuario **`compras.test`** · ítems de la FASE 10: 9

```http
POST http://127.0.0.1:8107/api/v1/companies/<EMPRESA_A>/purchases
```

```json
{
  "branch_id": "<SUCURSAL_A1>",
  "company_supplier_id": "<PROVEEDOR>",
  "operation_date": "<FECHA_NEGOCIO>",
  "payment_method_id": "<METODO_EFECTIVO>",
  "supplier_document_number": "FP1-<RUN_ID>",
  "lines": [
    {
      "company_product_id": "<PRODUCTO_EMPRESA_A>",
      "company_product_presentation_id": "<PRESENTACION_CAJA_EMPRESA_A>",
      "quantity": "2",
      "unit_cost": "12000"
    },
    {
      "company_product_id": "<PRODUCTO_EMPRESA_B>",
      "company_product_presentation_id": "<PRESENTACION_BASE_EMPRESA_B>",
      "quantity": "10",
      "unit_cost": "5000"
    }
  ]
}
```

**Permiso que exige la URL:** `perm:purchase:purchases:create` + `perm:purchase:purchase_details:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `compras.test` (por `perm:purchase:all:all`), `supervisor.test` (por `perm:all:all:create`)

**Por qué se hace así**

- `unit_cost` es por unidad de la línea (caja en P1); Inventory recibe la cantidad y el costo en unidad base.

**Respuesta esperada:** `201`

**Guardar:** `id` → `<COMPRA_1>`, `version` → `<COMPRA_1_VERSION>`

**Auditoría que deja:** `CREATE_PURCHASE` (purchase)

## 2. Registrar la compra P2 en borrador

Paso `P-01.P2` · usuario **`compras.test`** · ítems de la FASE 10: 9

```http
POST http://127.0.0.1:8107/api/v1/companies/<EMPRESA_A>/purchases
```

```json
{
  "branch_id": "<SUCURSAL_A1>",
  "company_supplier_id": "<PROVEEDOR>",
  "operation_date": "<FECHA_NEGOCIO>",
  "payment_method_id": "<METODO_EFECTIVO>",
  "supplier_document_number": "FP2-<RUN_ID>",
  "lines": [
    {
      "company_product_id": "<PRODUCTO_EMPRESA_A>",
      "company_product_presentation_id": "<PRESENTACION_BASE_EMPRESA_A>",
      "quantity": "26",
      "unit_cost": "1200"
    }
  ]
}
```

**Permiso que exige la URL:** `perm:purchase:purchases:create` + `perm:purchase:purchase_details:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `compras.test` (por `perm:purchase:all:all`), `supervisor.test` (por `perm:all:all:create`)

**Por qué se hace así**

- `unit_cost` es por unidad de la línea (caja en P1); Inventory recibe la cantidad y el costo en unidad base.

**Respuesta esperada:** `201`

**Guardar:** `id` → `<COMPRA_2>`, `version` → `<COMPRA_2_VERSION>`

**Auditoría que deja:** `CREATE_PURCHASE` (purchase)

## 3. Registrar la compra P3 en borrador

Paso `P-01.P3` · usuario **`compras.test`** · ítems de la FASE 10: 9

```http
POST http://127.0.0.1:8107/api/v1/companies/<EMPRESA_A>/purchases
```

```json
{
  "branch_id": "<SUCURSAL_A1>",
  "company_supplier_id": "<PROVEEDOR>",
  "operation_date": "<FECHA_NEGOCIO>",
  "payment_method_id": "<METODO_EFECTIVO>",
  "supplier_document_number": "FP3-<RUN_ID>",
  "lines": [
    {
      "company_product_id": "<PRODUCTO_EMPRESA_A>",
      "company_product_presentation_id": "<PRESENTACION_BASE_EMPRESA_A>",
      "quantity": "5",
      "unit_cost": "1300"
    }
  ]
}
```

**Permiso que exige la URL:** `perm:purchase:purchases:create` + `perm:purchase:purchase_details:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `compras.test` (por `perm:purchase:all:all`), `supervisor.test` (por `perm:all:all:create`)

**Por qué se hace así**

- `unit_cost` es por unidad de la línea (caja en P1); Inventory recibe la cantidad y el costo en unidad base.

**Respuesta esperada:** `201`

**Guardar:** `id` → `<COMPRA_3>`, `version` → `<COMPRA_3_VERSION>`

**Auditoría que deja:** `CREATE_PURCHASE` (purchase)

## 4. Registrar la compra P4 en borrador

Paso `P-01.P4` · usuario **`compras.test`** · ítems de la FASE 10: 9

```http
POST http://127.0.0.1:8107/api/v1/companies/<EMPRESA_A>/purchases
```

```json
{
  "branch_id": "<SUCURSAL_A1>",
  "company_supplier_id": "<PROVEEDOR>",
  "operation_date": "<FECHA_NEGOCIO>",
  "payment_method_id": "<METODO_EFECTIVO>",
  "supplier_document_number": "FP4-<RUN_ID>",
  "lines": [
    {
      "company_product_id": "<PRODUCTO_EMPRESA_A>",
      "company_product_presentation_id": "<PRESENTACION_BASE_EMPRESA_A>",
      "quantity": "1",
      "unit_cost": "1000"
    }
  ]
}
```

**Permiso que exige la URL:** `perm:purchase:purchases:create` + `perm:purchase:purchase_details:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `compras.test` (por `perm:purchase:all:all`), `supervisor.test` (por `perm:all:all:create`)

**Por qué se hace así**

- `unit_cost` es por unidad de la línea (caja en P1); Inventory recibe la cantidad y el costo en unidad base.

**Respuesta esperada:** `201`

**Guardar:** `id` → `<COMPRA_4>`, `version` → `<COMPRA_4_VERSION>`

**Auditoría que deja:** `CREATE_PURCHASE` (purchase)

## 5. Intentar una compra a crédito

Paso `P-01.credito` · usuario **`compras.test`** · ítems de la FASE 10: 9

```http
POST http://127.0.0.1:8107/api/v1/companies/<EMPRESA_A>/purchases
```

```json
{
  "branch_id": "<SUCURSAL_A1>",
  "company_supplier_id": "<PROVEEDOR>",
  "operation_date": "<FECHA_NEGOCIO>",
  "payment_method_id": "<METODO_EFECTIVO>",
  "supplier_payment_condition_id": "<CONDICION_CREDITO>",
  "lines": [
    {
      "company_product_id": "<PRODUCTO_EMPRESA_A>",
      "company_product_presentation_id": "<PRESENTACION_BASE_EMPRESA_A>",
      "quantity": "1",
      "unit_cost": "1000"
    }
  ]
}
```

**Permiso que exige la URL:** `perm:purchase:purchases:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `compras.test` (por `perm:purchase:all:all`), `supervisor.test` (por `perm:all:all:create`)

**Por qué se hace así**

- Spec 020: solo contado en el MVP; la condición CREDIT existe pero no es apta (`PAYMENT_CONDITION_NOT_AVAILABLE`).

**Respuesta esperada:** `409`
