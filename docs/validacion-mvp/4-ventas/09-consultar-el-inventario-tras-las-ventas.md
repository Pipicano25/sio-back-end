# Paso 09 de 09 — Consultar el inventario tras las ventas

Ejercicio 4 — Ventas con precio por presentación (lista indicada y predeterminada), rechazos, costo FIFO y margen · [Orden del ejercicio](ORDEN.md)

---

## 1. Saldo del producto A tras las ventas

Paso `V-07.saldo_a` · usuario **`supervisor.test`** · ítems de la FASE 10: 16, 17

```http
GET http://127.0.0.1:8109/api/v1/companies/<EMPRESA_A>/branches/<SUCURSAL_A1>/balances/<PRODUCTO_EMPRESA_A>
```

**Permiso que exige la URL:** `perm:inventory:balances:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `inventario.test` (por `perm:inventory:balances:read`)

**Respuesta esperada:** `200` — `quantity` = `23.0000`

## 2. Saldo del producto B tras las ventas

Paso `V-07.saldo_b` · usuario **`supervisor.test`** · ítems de la FASE 10: 16, 17

```http
GET http://127.0.0.1:8109/api/v1/companies/<EMPRESA_A>/branches/<SUCURSAL_A1>/balances/<PRODUCTO_EMPRESA_B>
```

**Permiso que exige la URL:** `perm:inventory:balances:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `inventario.test` (por `perm:inventory:balances:read`)

**Respuesta esperada:** `200` — `quantity` = `6.0000`

## 3. Kardex del producto A con las salidas

Paso `V-07.kardex_a` · usuario **`supervisor.test`** · ítems de la FASE 10: 16, 18

```http
GET http://127.0.0.1:8109/api/v1/companies/<EMPRESA_A>/branches/<SUCURSAL_A1>/kardex/<PRODUCTO_EMPRESA_A>?page_size=100
```

**Permiso que exige la URL:** `perm:inventory:movements:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `inventario.test` (por `perm:inventory:movements:read`)

**Respuesta esperada:** `200`

## 4. Kardex del producto B con la salida

Paso `V-07.kardex_b` · usuario **`supervisor.test`** · ítems de la FASE 10: 16, 18

```http
GET http://127.0.0.1:8109/api/v1/companies/<EMPRESA_A>/branches/<SUCURSAL_A1>/kardex/<PRODUCTO_EMPRESA_B>?page_size=100
```

**Permiso que exige la URL:** `perm:inventory:movements:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `inventario.test` (por `perm:inventory:movements:read`)

**Respuesta esperada:** `200`

## 5. Capas FIFO del producto A tras las ventas

Paso `V-07.capas_a` · usuario **`supervisor.test`** · ítems de la FASE 10: 16, 17

```http
GET http://127.0.0.1:8109/api/v1/companies/<EMPRESA_A>/branches/<SUCURSAL_A1>/valuation/<PRODUCTO_EMPRESA_A>/layers?include_closed=true
```

**Permiso que exige la URL:** `perm:inventory:valuation:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `inventario.test` (por `perm:inventory:valuation:read`)

**Respuesta esperada:** `200`

## 6. Capas FIFO del producto B tras las ventas

Paso `V-07.capas_b` · usuario **`supervisor.test`** · ítems de la FASE 10: 16, 17

```http
GET http://127.0.0.1:8109/api/v1/companies/<EMPRESA_A>/branches/<SUCURSAL_A1>/valuation/<PRODUCTO_EMPRESA_B>/layers?include_closed=true
```

**Permiso que exige la URL:** `perm:inventory:valuation:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `inventario.test` (por `perm:inventory:valuation:read`)

**Respuesta esperada:** `200`

## 7. Consumos de costo de la salida de V1

Paso `V-07.consumos_v1` · usuario **`supervisor.test`** · ítems de la FASE 10: 16

```http
GET http://127.0.0.1:8109/api/v1/companies/<EMPRESA_A>/inventory-movements/<MOVIMIENTO_V1>/cost-consumptions
```

**Permiso que exige la URL:** `perm:inventory:valuation:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `inventario.test` (por `perm:inventory:valuation:read`)

**Respuesta esperada:** `200`

## 8. Consumos de costo de la salida de V2

Paso `V-07.consumos_v2` · usuario **`supervisor.test`** · ítems de la FASE 10: 16

```http
GET http://127.0.0.1:8109/api/v1/companies/<EMPRESA_A>/inventory-movements/<MOVIMIENTO_V2>/cost-consumptions
```

**Permiso que exige la URL:** `perm:inventory:valuation:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `inventario.test` (por `perm:inventory:valuation:read`)

**Respuesta esperada:** `200`

## 9. Consumos de costo de la salida de V3

Paso `V-07.consumos_v3` · usuario **`supervisor.test`** · ítems de la FASE 10: 16

```http
GET http://127.0.0.1:8109/api/v1/companies/<EMPRESA_A>/inventory-movements/<MOVIMIENTO_V3>/cost-consumptions
```

**Permiso que exige la URL:** `perm:inventory:valuation:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `inventario.test` (por `perm:inventory:valuation:read`)

**Respuesta esperada:** `200`
