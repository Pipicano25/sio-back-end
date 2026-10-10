# Paso 04 de 04 — Consultar el inventario tras las compras

Ejercicio 3 — Compras e inventario: secuencias, compras, confirmación, entradas, saldos, kardex y capas · [Orden del ejercicio](ORDEN.md)

---

## 1. Consultar el saldo del producto A en A1

Paso `P-03.saldo_a` · usuario **`supervisor.test`** · ítems de la FASE 10: 11, 12

```http
GET http://127.0.0.1:8109/api/v1/companies/<EMPRESA_A>/branches/<SUCURSAL_A1>/balances/<PRODUCTO_EMPRESA_A>
```

**Permiso que exige la URL:** `perm:inventory:balances:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `inventario.test` (por `perm:inventory:balances:read`)

**Respuesta esperada:** `200` — `quantity` = `55.0000` tras las compras

## 2. Consultar el saldo del producto B en A1

Paso `P-03.saldo_b` · usuario **`supervisor.test`** · ítems de la FASE 10: 11, 12

```http
GET http://127.0.0.1:8109/api/v1/companies/<EMPRESA_A>/branches/<SUCURSAL_A1>/balances/<PRODUCTO_EMPRESA_B>
```

**Permiso que exige la URL:** `perm:inventory:balances:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `inventario.test` (por `perm:inventory:balances:read`)

**Respuesta esperada:** `200` — `quantity` = `10.0000`

## 3. Consultar el kardex del producto A

Paso `P-03.kardex_a` · usuario **`supervisor.test`** · ítems de la FASE 10: 11, 18

```http
GET http://127.0.0.1:8109/api/v1/companies/<EMPRESA_A>/branches/<SUCURSAL_A1>/kardex/<PRODUCTO_EMPRESA_A>?page_size=100
```

**Permiso que exige la URL:** `perm:inventory:movements:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `inventario.test` (por `perm:inventory:movements:read`)

**Respuesta esperada:** `200`

## 4. Consultar las capas FIFO del producto A

Paso `P-03.capas_a` · usuario **`supervisor.test`** · ítems de la FASE 10: 11, 12

```http
GET http://127.0.0.1:8109/api/v1/companies/<EMPRESA_A>/branches/<SUCURSAL_A1>/valuation/<PRODUCTO_EMPRESA_A>/layers?include_closed=true
```

**Permiso que exige la URL:** `perm:inventory:valuation:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `inventario.test` (por `perm:inventory:valuation:read`)

**Respuesta esperada:** `200`

## 5. Consultar las capas FIFO del producto B

Paso `P-03.capas_b` · usuario **`supervisor.test`** · ítems de la FASE 10: 11, 12

```http
GET http://127.0.0.1:8109/api/v1/companies/<EMPRESA_A>/branches/<SUCURSAL_A1>/valuation/<PRODUCTO_EMPRESA_B>/layers?include_closed=true
```

**Permiso que exige la URL:** `perm:inventory:valuation:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `inventario.test` (por `perm:inventory:valuation:read`)

**Respuesta esperada:** `200`
