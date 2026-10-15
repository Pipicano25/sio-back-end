# Paso 03 de 05 — Confirmar las compras

Ejercicio 3 — Compras e inventario: secuencias, compras de contado, confirmación, recepción física (entradas), saldos, kardex y capas · [Orden del ejercicio](ORDEN.md)

---

## 1. Confirmar la compra P1

Paso `P-02.P1` · usuario **`compras.test`** · ítems de la FASE 10: 10

```http
POST http://127.0.0.1:8107/api/v1/companies/<EMPRESA_A>/purchases/<COMPRA_1>/confirmation
Idempotency-Key: mvp-<RUN_ID>-P-02.P1-1
X-Correlation-Id: <UUID de la corrida y el paso>
```

```json
{
  "version": "<COMPRA_1_VERSION>"
}
```

**Permiso que exige la URL:** `perm:purchase:purchases:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `compras.test` (por `perm:purchase:all:all`), `supervisor.test` (por `perm:all:all:update`)

**Por qué se hace así**

- Spec 020: la confirmación asigna el número oficial y deja la compra pendiente de recepción; no mueve inventario.

**Respuesta esperada:** `200` — `status` = `CONFIRMED`, `number` asignado, `receipt_status` = `PENDING`, `inventory_operation_id` nulo

**Guardar:** `version` → `<COMPRA_1_VERSION>`, `number` → `<COMPRA_1_NUMERO>`

**Auditoría que deja:** `CONFIRM_PURCHASE` (purchase)

## 2. Confirmar la compra P2

Paso `P-02.P2` · usuario **`compras.test`** · ítems de la FASE 10: 10

```http
POST http://127.0.0.1:8107/api/v1/companies/<EMPRESA_A>/purchases/<COMPRA_2>/confirmation
Idempotency-Key: mvp-<RUN_ID>-P-02.P2-1
X-Correlation-Id: <UUID de la corrida y el paso>
```

```json
{
  "version": "<COMPRA_2_VERSION>"
}
```

**Permiso que exige la URL:** `perm:purchase:purchases:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `compras.test` (por `perm:purchase:all:all`), `supervisor.test` (por `perm:all:all:update`)

**Por qué se hace así**

- Spec 020: la confirmación asigna el número oficial y deja la compra pendiente de recepción; no mueve inventario.

**Respuesta esperada:** `200` — `status` = `CONFIRMED`, `number` asignado, `receipt_status` = `PENDING`, `inventory_operation_id` nulo

**Guardar:** `version` → `<COMPRA_2_VERSION>`, `number` → `<COMPRA_2_NUMERO>`

**Auditoría que deja:** `CONFIRM_PURCHASE` (purchase)

## 3. Confirmar la compra P3

Paso `P-02.P3` · usuario **`compras.test`** · ítems de la FASE 10: 10

```http
POST http://127.0.0.1:8107/api/v1/companies/<EMPRESA_A>/purchases/<COMPRA_3>/confirmation
Idempotency-Key: mvp-<RUN_ID>-P-02.P3-1
X-Correlation-Id: <UUID de la corrida y el paso>
```

```json
{
  "version": "<COMPRA_3_VERSION>"
}
```

**Permiso que exige la URL:** `perm:purchase:purchases:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `compras.test` (por `perm:purchase:all:all`), `supervisor.test` (por `perm:all:all:update`)

**Por qué se hace así**

- Spec 020: la confirmación asigna el número oficial y deja la compra pendiente de recepción; no mueve inventario.

**Respuesta esperada:** `200` — `status` = `CONFIRMED`, `number` asignado, `receipt_status` = `PENDING`, `inventory_operation_id` nulo

**Guardar:** `version` → `<COMPRA_3_VERSION>`, `number` → `<COMPRA_3_NUMERO>`

**Auditoría que deja:** `CONFIRM_PURCHASE` (purchase)
