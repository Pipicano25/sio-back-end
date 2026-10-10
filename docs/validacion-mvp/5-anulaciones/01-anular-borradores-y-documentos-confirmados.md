# Paso 01 de 03 — Anular borradores y documentos confirmados

Ejercicio 5 — Anulaciones y reversos · [Orden del ejercicio](ORDEN.md)

---

## 1. Anular la compra P4

Paso `A-01.P4` · usuario **`compras.test`** · ítems de la FASE 10: 20

```http
POST http://127.0.0.1:8107/api/v1/companies/<EMPRESA_A>/purchases/<COMPRA_4>/cancellation
Idempotency-Key: mvp-<RUN_ID>-A-01.P4-1
X-Correlation-Id: <UUID de la corrida y el paso>
```

```json
{
  "version": "<COMPRA_4_VERSION>",
  "reason": "Anulación de validación MVP <RUN_ID> (dato ficticio)"
}
```

**Permiso que exige la URL:** `perm:purchase:purchases:delete`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `compras.test` (por `perm:purchase:all:all`)

**Respuesta esperada:** `200`

**Guardar:** `version` → `<COMPRA_4_VERSION>`

**Auditoría que deja:** `CANCEL_PURCHASE` (purchase)

## 2. Anular la venta V6

Paso `A-01.V6` · usuario **`ventas.test`** · ítems de la FASE 10: 20

```http
POST http://127.0.0.1:8108/api/v1/companies/<EMPRESA_A>/sales/<VENTA_6>/cancellation
Idempotency-Key: mvp-<RUN_ID>-A-01.V6-1
X-Correlation-Id: <UUID de la corrida y el paso>
```

```json
{
  "version": "<VENTA_6_VERSION>",
  "reason": "Anulación de validación MVP <RUN_ID> (dato ficticio)"
}
```

**Permiso que exige la URL:** `perm:sales:sales:delete`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `ventas.test` (por `perm:sales:all:delete`)

**Respuesta esperada:** `200`

**Guardar:** `version` → `<VENTA_6_VERSION>`

**Auditoría que deja:** `CANCEL_SALE` (sales)

## 3. Anular la venta V3

Paso `A-01.V3` · usuario **`ventas.test`** · ítems de la FASE 10: 20

```http
POST http://127.0.0.1:8108/api/v1/companies/<EMPRESA_A>/sales/<VENTA_3>/cancellation
Idempotency-Key: mvp-<RUN_ID>-A-01.V3-1
X-Correlation-Id: <UUID de la corrida y el paso>
```

```json
{
  "version": "<VENTA_3_VERSION>",
  "reason": "Anulación de validación MVP <RUN_ID> (dato ficticio)"
}
```

**Permiso que exige la URL:** `perm:sales:sales:delete`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `ventas.test` (por `perm:sales:all:delete`)

**Respuesta esperada:** `200`

**Guardar:** `version` → `<VENTA_3_VERSION>`

**Auditoría que deja:** `CANCEL_SALE` (sales)

## 4. Anular la compra P3

Paso `A-01.P3` · usuario **`compras.test`** · ítems de la FASE 10: 20

```http
POST http://127.0.0.1:8107/api/v1/companies/<EMPRESA_A>/purchases/<COMPRA_3>/cancellation
Idempotency-Key: mvp-<RUN_ID>-A-01.P3-1
X-Correlation-Id: <UUID de la corrida y el paso>
```

```json
{
  "version": "<COMPRA_3_VERSION>",
  "reason": "Anulación de validación MVP <RUN_ID> (dato ficticio)"
}
```

**Permiso que exige la URL:** `perm:purchase:purchases:delete`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `compras.test` (por `perm:purchase:all:all`)

**Respuesta esperada:** `200`

**Guardar:** `version` → `<COMPRA_3_VERSION>`

**Auditoría que deja:** `CANCEL_PURCHASE` (purchase)

## 5. Consultar las operaciones de la venta anulada

Paso `A-01.operaciones_V3` · usuario **`ventas.test`** · ítems de la FASE 10: 20

```http
GET http://127.0.0.1:8108/api/v1/companies/<EMPRESA_A>/sales/<VENTA_3>/operations
```

**Permiso que exige la URL:** `perm:sales:sale_operations:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `ventas.test` (por `perm:sales:all:read`), `supervisor.test` (por `perm:all:all:read`), `consulta.test` (por `perm:sales:sale_operations:read`), `reportes.test` (por `perm:sales:sale_operations:read`)

**Por qué se hace así**

- La operación de anulación guarda el id de la operación de reverso de Inventory.

**Respuesta esperada:** `200`

## 6. Consultar las operaciones de la compra anulada

Paso `A-01.operaciones_P3` · usuario **`compras.test`** · ítems de la FASE 10: 20

```http
GET http://127.0.0.1:8107/api/v1/companies/<EMPRESA_A>/purchases/<COMPRA_3>/operations
```

**Permiso que exige la URL:** `perm:purchase:purchase_operations:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `compras.test` (por `perm:purchase:all:all`), `supervisor.test` (por `perm:all:all:read`), `consulta.test` (por `perm:purchase:purchase_operations:read`), `reportes.test` (por `perm:purchase:purchase_operations:read`)

**Por qué se hace así**

- La operación de anulación guarda el id de la operación de reverso de Inventory.

**Respuesta esperada:** `200`
