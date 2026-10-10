# Paso 10 de 12 — Permisos: la cuenta de servicio de Sales no vende

Ejercicio 7 — Seguridad entre empresas y permisos · [Orden del ejercicio](ORDEN.md)

---

## 1. La cuenta de servicio sales-service intenta registrar una venta

Paso `S-04.crear` · usuario **`service-account-sales-service`** · ítems de la FASE 10: 21

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
      "quantity": "1"
    }
  ]
}
```

**Permiso que exige la URL:** `perm:sales:sales:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `ventas.test` (por `perm:sales:all:create`), `supervisor.test` (por `perm:all:all:create`)

**Respuesta esperada:** `403`

## 2. La cuenta de servicio sales-service intenta confirmar la venta V4

Paso `S-04.confirmar` · usuario **`service-account-sales-service`** · ítems de la FASE 10: 21

```http
POST http://127.0.0.1:8108/api/v1/companies/<EMPRESA_A>/sales/<VENTA_4>/confirmation
Idempotency-Key: mvp-<RUN_ID>-S-04.confirmar-1
X-Correlation-Id: <UUID de la corrida y el paso>
```

```json
{
  "version": "<VENTA_4_VERSION>"
}
```

**Permiso que exige la URL:** `perm:sales:sales:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `ventas.test` (por `perm:sales:all:update`), `supervisor.test` (por `perm:all:all:update`)

**Respuesta esperada:** `403`
