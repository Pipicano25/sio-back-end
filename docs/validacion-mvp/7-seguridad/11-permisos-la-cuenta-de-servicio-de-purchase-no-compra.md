# Paso 11 de 12 — Permisos: la cuenta de servicio de Purchase no compra

Ejercicio 7 — Seguridad entre empresas y permisos · [Orden del ejercicio](ORDEN.md)

---

## 1. La cuenta de servicio purchase-service intenta registrar una compra

Paso `S-05.crear` · usuario **`service-account-purchase-service`** · ítems de la FASE 10: 21

```http
POST http://127.0.0.1:8107/api/v1/companies/<EMPRESA_A>/purchases
```

```json
{
  "branch_id": "<SUCURSAL_A1>",
  "company_supplier_id": "<PROVEEDOR>",
  "operation_date": "<FECHA_NEGOCIO>",
  "lines": [
    {
      "company_product_id": "<PRODUCTO_EMPRESA_A>",
      "quantity": "1",
      "unit_cost": "1000"
    }
  ]
}
```

**Permiso que exige la URL:** `perm:purchase:purchases:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `compras.test` (por `perm:purchase:all:all`), `supervisor.test` (por `perm:all:all:create`)

**Respuesta esperada:** `403`

## 2. La cuenta de servicio purchase-service intenta confirmar la compra P1

Paso `S-05.confirmar` · usuario **`service-account-purchase-service`** · ítems de la FASE 10: 21

```http
POST http://127.0.0.1:8107/api/v1/companies/<EMPRESA_A>/purchases/<COMPRA_1>/confirmation
Idempotency-Key: mvp-<RUN_ID>-S-05.confirmar-1
X-Correlation-Id: <UUID de la corrida y el paso>
```

```json
{
  "version": "<COMPRA_1_VERSION>"
}
```

**Permiso que exige la URL:** `perm:purchase:purchases:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `compras.test` (por `perm:purchase:all:all`), `supervisor.test` (por `perm:all:all:update`)

**Respuesta esperada:** `403`
