# Paso 05 de 08 — Rechazo por precio cambiado

Ejercicio 4 — Ventas con los tres mecanismos de precio, rechazos, costo FIFO y margen · [Orden del ejercicio](ORDEN.md)

---

## 1. Cambiar el precio de la unidad del producto A en GENERAL (1 500 → 1 550)

Paso `V-05.cambio` · usuario **`admin.test`** · ítems de la FASE 10: 15

```http
POST http://127.0.0.1:8106/api/v1/price-list-items/<ITEM_GENERAL>/change-price
```

```json
{
  "unit_price": "1550.00",
  "version": "<ITEM_GENERAL_VERSION>"
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:price_list_items:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)

**Por qué se hace así**

- El precio vigente cambia entre el borrador de V5 y su confirmación.

**Respuesta esperada:** `201`

**Guardar:** `item.id` → `<ITEM_GENERAL_NUEVO>`

**Auditoría que deja:** `CHANGE_PRICE_LIST_ITEM_PRICE` (commercial-relationship)

## 2. Confirmar la venta V5 (rechazada)

Paso `V-05.V5` · usuario **`ventas.test`** · ítems de la FASE 10: 15

```http
POST http://127.0.0.1:8108/api/v1/companies/<EMPRESA_A>/sales/<VENTA_5>/confirmation
Idempotency-Key: mvp-<RUN_ID>-V-05.V5-1
X-Correlation-Id: <UUID de la corrida y el paso>
```

```json
{
  "version": "<VENTA_5_VERSION>"
}
```

**Permiso que exige la URL:** `perm:sales:sales:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `ventas.test` (por `perm:sales:all:update`), `supervisor.test` (por `perm:all:all:update`)

**Respuesta esperada:** `409`
