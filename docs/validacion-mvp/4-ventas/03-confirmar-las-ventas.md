# Paso 03 de 08 — Confirmar las ventas

Ejercicio 4 — Ventas con precio por presentación (lista indicada y predeterminada), rechazos, costo FIFO y margen · [Orden del ejercicio](ORDEN.md)

---

## 1. Confirmar la venta V1

Paso `V-03.V1` · usuario **`ventas.test`** · ítems de la FASE 10: 15

```http
POST http://127.0.0.1:8108/api/v1/companies/<EMPRESA_A>/sales/<VENTA_1>/confirmation
Idempotency-Key: mvp-<RUN_ID>-V-03.V1-1
X-Correlation-Id: <UUID de la corrida y el paso>
```

```json
{
  "version": "<VENTA_1_VERSION>"
}
```

**Permiso que exige la URL:** `perm:sales:sales:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `ventas.test` (por `perm:sales:all:update`), `supervisor.test` (por `perm:all:all:update`)

**Respuesta esperada:** `200`

**Guardar:** `version` → `<VENTA_1_VERSION>`, `number` → `<VENTA_1_NUMERO>`, `inventory_operation_id` → `<VENTA_1_OPERACION>`

**Auditoría que deja:** `CONFIRM_SALE` (sales), `APPLY_INVENTORY_OUTPUT` (inventory)

## 2. Confirmar la venta V2

Paso `V-03.V2` · usuario **`ventas.test`** · ítems de la FASE 10: 15

```http
POST http://127.0.0.1:8108/api/v1/companies/<EMPRESA_A>/sales/<VENTA_2>/confirmation
Idempotency-Key: mvp-<RUN_ID>-V-03.V2-1
X-Correlation-Id: <UUID de la corrida y el paso>
```

```json
{
  "version": "<VENTA_2_VERSION>"
}
```

**Permiso que exige la URL:** `perm:sales:sales:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `ventas.test` (por `perm:sales:all:update`), `supervisor.test` (por `perm:all:all:update`)

**Respuesta esperada:** `200`

**Guardar:** `version` → `<VENTA_2_VERSION>`, `number` → `<VENTA_2_NUMERO>`, `inventory_operation_id` → `<VENTA_2_OPERACION>`

**Auditoría que deja:** `CONFIRM_SALE` (sales), `APPLY_INVENTORY_OUTPUT` (inventory)

## 3. Confirmar la venta V3

Paso `V-03.V3` · usuario **`ventas.test`** · ítems de la FASE 10: 15

```http
POST http://127.0.0.1:8108/api/v1/companies/<EMPRESA_A>/sales/<VENTA_3>/confirmation
Idempotency-Key: mvp-<RUN_ID>-V-03.V3-1
X-Correlation-Id: <UUID de la corrida y el paso>
```

```json
{
  "version": "<VENTA_3_VERSION>"
}
```

**Permiso que exige la URL:** `perm:sales:sales:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `ventas.test` (por `perm:sales:all:update`), `supervisor.test` (por `perm:all:all:update`)

**Respuesta esperada:** `200`

**Guardar:** `version` → `<VENTA_3_VERSION>`, `number` → `<VENTA_3_NUMERO>`, `inventory_operation_id` → `<VENTA_3_OPERACION>`

**Auditoría que deja:** `CONFIRM_SALE` (sales), `APPLY_INVENTORY_OUTPUT` (inventory)
