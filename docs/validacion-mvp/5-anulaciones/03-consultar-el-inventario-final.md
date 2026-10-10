# Paso 03 de 03 — Consultar el inventario final

Ejercicio 5 — Anulaciones y reversos · [Orden del ejercicio](ORDEN.md)

---

## 1. Saldo final del producto A

Paso `A-03.saldo_a` · usuario **`supervisor.test`** · ítems de la FASE 10: 17, 20

```http
GET http://127.0.0.1:8109/api/v1/companies/<EMPRESA_A>/branches/<SUCURSAL_A1>/balances/<PRODUCTO_EMPRESA_A>
```

**Permiso que exige la URL:** `perm:inventory:balances:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `inventario.test` (por `perm:inventory:balances:read`)

**Respuesta esperada:** `200` — `quantity` = `18.0000`

## 2. Saldo final del producto B

Paso `A-03.saldo_b` · usuario **`supervisor.test`** · ítems de la FASE 10: 17, 20

```http
GET http://127.0.0.1:8109/api/v1/companies/<EMPRESA_A>/branches/<SUCURSAL_A1>/balances/<PRODUCTO_EMPRESA_B>
```

**Permiso que exige la URL:** `perm:inventory:balances:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `inventario.test` (por `perm:inventory:balances:read`)

**Respuesta esperada:** `200` — `quantity` = `10.0000`

## 3. Kardex final del producto A

Paso `A-03.kardex_a` · usuario **`supervisor.test`** · ítems de la FASE 10: 18, 20

```http
GET http://127.0.0.1:8109/api/v1/companies/<EMPRESA_A>/branches/<SUCURSAL_A1>/kardex/<PRODUCTO_EMPRESA_A>?page_size=100
```

**Permiso que exige la URL:** `perm:inventory:movements:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `inventario.test` (por `perm:inventory:movements:read`)

**Respuesta esperada:** `200`

## 4. Kardex final del producto B

Paso `A-03.kardex_b` · usuario **`supervisor.test`** · ítems de la FASE 10: 18, 20

```http
GET http://127.0.0.1:8109/api/v1/companies/<EMPRESA_A>/branches/<SUCURSAL_A1>/kardex/<PRODUCTO_EMPRESA_B>?page_size=100
```

**Permiso que exige la URL:** `perm:inventory:movements:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `inventario.test` (por `perm:inventory:movements:read`)

**Respuesta esperada:** `200`

## 5. Capas finales del producto A

Paso `A-03.capas_a` · usuario **`supervisor.test`** · ítems de la FASE 10: 17, 20

```http
GET http://127.0.0.1:8109/api/v1/companies/<EMPRESA_A>/branches/<SUCURSAL_A1>/valuation/<PRODUCTO_EMPRESA_A>/layers?include_closed=true
```

**Permiso que exige la URL:** `perm:inventory:valuation:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `inventario.test` (por `perm:inventory:valuation:read`)

**Respuesta esperada:** `200`

## 6. Capas finales del producto B

Paso `A-03.capas_b` · usuario **`supervisor.test`** · ítems de la FASE 10: 17, 20

```http
GET http://127.0.0.1:8109/api/v1/companies/<EMPRESA_A>/branches/<SUCURSAL_A1>/valuation/<PRODUCTO_EMPRESA_B>/layers?include_closed=true
```

**Permiso que exige la URL:** `perm:inventory:valuation:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `inventario.test` (por `perm:inventory:valuation:read`)

**Respuesta esperada:** `200`

## 7. Valoración final de la sucursal A1

Paso `A-03.valoracion` · usuario **`supervisor.test`** · ítems de la FASE 10: 17, 20

```http
GET http://127.0.0.1:8109/api/v1/companies/<EMPRESA_A>/branches/<SUCURSAL_A1>/valuation?page_size=100
```

**Permiso que exige la URL:** `perm:inventory:valuation:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `inventario.test` (por `perm:inventory:valuation:read`)

**Respuesta esperada:** `200`
