# Paso 02 de 03 — Rechazo al anular una compra consumida

Ejercicio 5 — Anulaciones y reversos · [Orden del ejercicio](ORDEN.md)

---

## 1. Anular la compra P1 (rechazada)

Paso `A-02.P1` · usuario **`compras.test`** · ítems de la FASE 10: 20

```http
POST http://127.0.0.1:8107/api/v1/companies/<EMPRESA_A>/purchases/<COMPRA_1>/cancellation
Idempotency-Key: mvp-<RUN_ID>-A-02.P1-1
X-Correlation-Id: <UUID de la corrida y el paso>
```

```json
{
  "version": "<COMPRA_1_VERSION>",
  "reason": "Anulación de validación MVP <RUN_ID> (dato ficticio)"
}
```

**Permiso que exige la URL:** `perm:purchase:purchases:delete`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `compras.test` (por `perm:purchase:all:all`)

**Respuesta esperada:** `409`

**Auditoría que deja:** `CANCEL_PURCHASE` (purchase)
