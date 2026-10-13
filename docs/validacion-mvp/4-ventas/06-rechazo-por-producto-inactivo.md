# Paso 06 de 08 — Rechazo por producto inactivo

Ejercicio 4 — Ventas con precio por presentación (lista indicada y predeterminada), rechazos, costo FIFO y margen · [Orden del ejercicio](ORDEN.md)

---

## 1. Inactivar el producto B de la empresa A

Paso `V-05b.inactivar` · usuario **`admin.test`** · ítems de la FASE 10: 15

```http
POST http://127.0.0.1:8106/api/v1/company-products/<PRODUCTO_EMPRESA_B>/deactivate
```

```json
{
  "version": "<PRODUCTO_EMPRESA_B_VERSION>"
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_products:delete`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`)

**Respuesta esperada:** `200`

**Guardar:** `version` → `<PRODUCTO_EMPRESA_B_VERSION>`

**Auditoría que deja:** `DEACTIVATE_COMPANY_PRODUCT` (commercial-relationship)

## 2. Confirmar la venta V7 con el producto inactivo (rechazada)

Paso `V-05b.V7` · usuario **`ventas.test`** · ítems de la FASE 10: 15

```http
POST http://127.0.0.1:8108/api/v1/companies/<EMPRESA_A>/sales/<VENTA_7>/confirmation
Idempotency-Key: mvp-<RUN_ID>-V-05b.V7-1
X-Correlation-Id: <UUID de la corrida y el paso>
```

```json
{
  "version": "<VENTA_7_VERSION>"
}
```

**Permiso que exige la URL:** `perm:sales:sales:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `ventas.test` (por `perm:sales:all:update`), `supervisor.test` (por `perm:all:all:update`)

**Respuesta esperada:** `409`

## 3. Reactivar el producto B de la empresa A

Paso `V-05b.reactivar` · usuario **`admin.test`** · ítems de la FASE 10: 15

```http
POST http://127.0.0.1:8106/api/v1/company-products/<PRODUCTO_EMPRESA_B>/reactivate
```

```json
{
  "version": "<PRODUCTO_EMPRESA_B_VERSION>"
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)

**Respuesta esperada:** `200`

**Guardar:** `version` → `<PRODUCTO_EMPRESA_B_VERSION>`

**Auditoría que deja:** `REACTIVATE_COMPANY_PRODUCT` (commercial-relationship)
