# Paso 05 de 05 — Consultar el inventario tras las compras

Ejercicio 3 — Compras e inventario: secuencias, compras de contado, confirmación, recepción física (entradas), saldos, kardex y capas · [Orden del ejercicio](ORDEN.md)

---

## 1. Consultar el precio automático de la caja en AUTOMATICA

Paso `P-03.precio_automatico` · usuario **`admin.test`** · ítems de la FASE 10: 10, 11

```http
GET http://127.0.0.1:8106/api/v1/companies/<EMPRESA_A>/price-list-items?price_list_id=<LISTA_AUTOMATICA>
```

**Permiso que exige la URL:** `perm:commercial-relationship:price_list_items:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `compras.test` (por `perm:commercial-relationship:price_list_items:read`), `ventas.test` (por `perm:commercial-relationship:price_list_items:read`), `supervisor.test` (por `perm:commercial-relationship:all:read`), `inventario.test` (por `perm:commercial-relationship:price_list_items:read`)

**Por qué se hace así**

- Spec 021: compra → recepción física → precio automático. El costo FIFO de Inventory no cambia (sin impuestos).

**Respuesta esperada:** `200` — la caja: `unit_price` = `15600.00` y `origin` = `AUTOMATIC` (12 000 por caja en P1, tasa 0 %, × 1,30); las unidades de A y B también reciben su precio automático en AUTOMATICA (las ventas usan GENERAL y MAYORISTA); lo aplica el worker de precios después de la recepción

## 2. Consultar el saldo del producto A en A1

Paso `P-03.saldo_a` · usuario **`supervisor.test`** · ítems de la FASE 10: 11, 12

```http
GET http://127.0.0.1:8109/api/v1/companies/<EMPRESA_A>/branches/<SUCURSAL_A1>/balances/<PRODUCTO_EMPRESA_A>
```

**Permiso que exige la URL:** `perm:inventory:balances:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `compras.test` (por `perm:inventory:balances:read`), `ventas.test` (por `perm:inventory:balances:read`), `supervisor.test` (por `perm:inventory:balances:read`), `inventario.test` (por `perm:inventory:balances:read`)

**Respuesta esperada:** `200` — `quantity` = `55.0000` tras las compras

## 3. Consultar el saldo del producto B en A1

Paso `P-03.saldo_b` · usuario **`supervisor.test`** · ítems de la FASE 10: 11, 12

```http
GET http://127.0.0.1:8109/api/v1/companies/<EMPRESA_A>/branches/<SUCURSAL_A1>/balances/<PRODUCTO_EMPRESA_B>
```

**Permiso que exige la URL:** `perm:inventory:balances:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `compras.test` (por `perm:inventory:balances:read`), `ventas.test` (por `perm:inventory:balances:read`), `supervisor.test` (por `perm:inventory:balances:read`), `inventario.test` (por `perm:inventory:balances:read`)

**Respuesta esperada:** `200` — `quantity` = `10.0000`

## 4. Consultar el kardex del producto A

Paso `P-03.kardex_a` · usuario **`supervisor.test`** · ítems de la FASE 10: 11, 18

```http
GET http://127.0.0.1:8109/api/v1/companies/<EMPRESA_A>/branches/<SUCURSAL_A1>/kardex/<PRODUCTO_EMPRESA_A>?page_size=100
```

**Permiso que exige la URL:** `perm:inventory:movements:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `compras.test` (por `perm:inventory:movements:read`), `ventas.test` (por `perm:inventory:movements:read`), `supervisor.test` (por `perm:inventory:movements:read`), `inventario.test` (por `perm:inventory:movements:read`)

**Respuesta esperada:** `200`

## 5. Consultar las capas FIFO del producto A

Paso `P-03.capas_a` · usuario **`supervisor.test`** · ítems de la FASE 10: 11, 12

```http
GET http://127.0.0.1:8109/api/v1/companies/<EMPRESA_A>/branches/<SUCURSAL_A1>/valuation/<PRODUCTO_EMPRESA_A>/layers?include_closed=true
```

**Permiso que exige la URL:** `perm:inventory:valuation:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `compras.test` (por `perm:inventory:valuation:read`), `ventas.test` (por `perm:inventory:valuation:read`), `supervisor.test` (por `perm:inventory:valuation:read`), `inventario.test` (por `perm:inventory:valuation:read`)

**Respuesta esperada:** `200`

## 6. Consultar las capas FIFO del producto B

Paso `P-03.capas_b` · usuario **`supervisor.test`** · ítems de la FASE 10: 11, 12

```http
GET http://127.0.0.1:8109/api/v1/companies/<EMPRESA_A>/branches/<SUCURSAL_A1>/valuation/<PRODUCTO_EMPRESA_B>/layers?include_closed=true
```

**Permiso que exige la URL:** `perm:inventory:valuation:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `compras.test` (por `perm:inventory:valuation:read`), `ventas.test` (por `perm:inventory:valuation:read`), `supervisor.test` (por `perm:inventory:valuation:read`), `inventario.test` (por `perm:inventory:valuation:read`)

**Respuesta esperada:** `200`
