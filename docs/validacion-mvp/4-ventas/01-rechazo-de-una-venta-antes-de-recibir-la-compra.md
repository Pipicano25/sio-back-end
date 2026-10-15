# Paso 01 de 09 — Rechazo de una venta antes de recibir la compra

Ejercicio 4 — Ventas con precio por presentación (lista indicada y predeterminada), rechazos, costo FIFO y margen · [Orden del ejercicio](ORDEN.md)

---

## 1. Registrar la venta V0 en borrador

Paso `V-00.V0-borrador` · usuario **`ventas.test`** · ítems de la FASE 10: 13

```http
POST http://127.0.0.1:8108/api/v1/companies/<EMPRESA_A>/sales
```

```json
{
  "branch_id": "<SUCURSAL_A1>",
  "company_customer_id": "<CLIENTE>",
  "payment_method_id": "<METODO_EFECTIVO>",
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

- Spec 020: producto B con la compra P1 confirmada pero aún no recibida

**Respuesta esperada:** `201`

**Guardar:** `id` → `<VENTA_0>`, `version` → `<VENTA_0_VERSION>`

**Auditoría que deja:** `CREATE_SALE` (sales)

## 2. Confirmar la venta V0 (rechazada)

Paso `V-00.V0` · usuario **`ventas.test`** · ítems de la FASE 10: 14, 15

```http
POST http://127.0.0.1:8108/api/v1/companies/<EMPRESA_A>/sales/<VENTA_0>/confirmation
Idempotency-Key: mvp-<RUN_ID>-V-00.V0-1
X-Correlation-Id: <UUID de la corrida y el paso>
```

```json
{
  "version": "<VENTA_0_VERSION>"
}
```

**Permiso que exige la URL:** `perm:sales:sales:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `ventas.test` (por `perm:sales:all:update`), `supervisor.test` (por `perm:all:all:update`)

**Respuesta esperada:** `409`
