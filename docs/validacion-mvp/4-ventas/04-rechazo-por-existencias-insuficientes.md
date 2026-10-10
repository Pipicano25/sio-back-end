# Paso 04 de 08 — Rechazo por existencias insuficientes

Ejercicio 4 — Ventas con los tres mecanismos de precio, rechazos, costo FIFO y margen · [Orden del ejercicio](ORDEN.md)

---

## 1. Confirmar la venta V4 (rechazada)

Paso `V-04.V4` · usuario **`ventas.test`** · ítems de la FASE 10: 14

```http
POST http://127.0.0.1:8108/api/v1/companies/<EMPRESA_A>/sales/<VENTA_4>/confirmation
Idempotency-Key: mvp-<RUN_ID>-V-04.V4-1
X-Correlation-Id: <UUID de la corrida y el paso>
```

```json
{
  "version": "<VENTA_4_VERSION>"
}
```

**Permiso que exige la URL:** `perm:sales:sales:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `ventas.test` (por `perm:sales:all:update`), `supervisor.test` (por `perm:all:all:update`)

**Respuesta esperada:** `409`
