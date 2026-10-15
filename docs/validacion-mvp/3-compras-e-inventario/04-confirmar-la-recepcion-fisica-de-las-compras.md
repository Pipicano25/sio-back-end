# Paso 04 de 05 — Confirmar la recepción física de las compras

Ejercicio 3 — Compras e inventario: secuencias, compras de contado, confirmación, recepción física (entradas), saldos, kardex y capas · [Orden del ejercicio](ORDEN.md)

---

## 1. Confirmar la recepción física completa de la compra P1

Paso `P-02R.P1` · usuario **`compras.test`** · ítems de la FASE 10: 10, 11

```http
POST http://127.0.0.1:8107/api/v1/companies/<EMPRESA_A>/purchases/<COMPRA_1>/receipt
Idempotency-Key: mvp-<RUN_ID>-P-02R.P1-1
X-Correlation-Id: <UUID de la corrida y el paso>
```

```json
{
  "version": "<COMPRA_1_VERSION>",
  "full_receipt_confirmed": true
}
```

**Permiso que exige la URL:** `perm:purchase:purchases:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `compras.test` (por `perm:purchase:all:all`), `supervisor.test` (por `perm:all:all:update`)

**Por qué se hace así**

- Spec 020: solo la recepción completa registra la entrada en Inventory, una sola vez (Idempotency-Key), y crea las capas FIFO.

**Respuesta esperada:** `200` — `receipt_status` = `RECEIVED`, `received_at`, `received_by_user_id`, `inventory_operation_id`

**Guardar:** `version` → `<COMPRA_1_VERSION>`, `inventory_operation_id` → `<COMPRA_1_OPERACION>`

**Auditoría que deja:** `RECEIVE_PURCHASE` (purchase), `APPLY_INVENTORY_ENTRY` (inventory)

## 2. Confirmar la recepción física completa de la compra P2

Paso `P-02R.P2` · usuario **`compras.test`** · ítems de la FASE 10: 10, 11

```http
POST http://127.0.0.1:8107/api/v1/companies/<EMPRESA_A>/purchases/<COMPRA_2>/receipt
Idempotency-Key: mvp-<RUN_ID>-P-02R.P2-1
X-Correlation-Id: <UUID de la corrida y el paso>
```

```json
{
  "version": "<COMPRA_2_VERSION>",
  "full_receipt_confirmed": true
}
```

**Permiso que exige la URL:** `perm:purchase:purchases:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `compras.test` (por `perm:purchase:all:all`), `supervisor.test` (por `perm:all:all:update`)

**Por qué se hace así**

- Spec 020: solo la recepción completa registra la entrada en Inventory, una sola vez (Idempotency-Key), y crea las capas FIFO.

**Respuesta esperada:** `200` — `receipt_status` = `RECEIVED`, `received_at`, `received_by_user_id`, `inventory_operation_id`

**Guardar:** `version` → `<COMPRA_2_VERSION>`, `inventory_operation_id` → `<COMPRA_2_OPERACION>`

**Auditoría que deja:** `RECEIVE_PURCHASE` (purchase), `APPLY_INVENTORY_ENTRY` (inventory)

## 3. Confirmar la recepción física completa de la compra P3

Paso `P-02R.P3` · usuario **`compras.test`** · ítems de la FASE 10: 10, 11

```http
POST http://127.0.0.1:8107/api/v1/companies/<EMPRESA_A>/purchases/<COMPRA_3>/receipt
Idempotency-Key: mvp-<RUN_ID>-P-02R.P3-1
X-Correlation-Id: <UUID de la corrida y el paso>
```

```json
{
  "version": "<COMPRA_3_VERSION>",
  "full_receipt_confirmed": true
}
```

**Permiso que exige la URL:** `perm:purchase:purchases:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `compras.test` (por `perm:purchase:all:all`), `supervisor.test` (por `perm:all:all:update`)

**Por qué se hace así**

- Spec 020: solo la recepción completa registra la entrada en Inventory, una sola vez (Idempotency-Key), y crea las capas FIFO.

**Respuesta esperada:** `200` — `receipt_status` = `RECEIVED`, `received_at`, `received_by_user_id`, `inventory_operation_id`

**Guardar:** `version` → `<COMPRA_3_VERSION>`, `inventory_operation_id` → `<COMPRA_3_OPERACION>`

**Auditoría que deja:** `RECEIVE_PURCHASE` (purchase), `APPLY_INVENTORY_ENTRY` (inventory)
