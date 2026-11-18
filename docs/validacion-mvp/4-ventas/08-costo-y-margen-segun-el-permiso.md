# Paso 08 de 09 — Costo y margen según el permiso

Ejercicio 4 — Ventas con precio por presentación (lista indicada y predeterminada), rechazos, costo FIFO y margen · [Orden del ejercicio](ORDEN.md)

---

## 1. Consultar la venta V2 como operario (sin costo ni margen)

Paso `V-06.vendedor` · usuario **`operario.dao`** · ítems de la FASE 10: 16

```http
GET http://127.0.0.1:8108/api/v1/companies/<EMPRESA_A>/sales/<VENTA_2>
```

**Permiso que exige la URL:** `perm:sales:sales:read`

- ✅ **Pueden:** `admin.sio` (por `perm:all:all:all`), `admin.dao` (por `perm:sales:all:all`), `operario.dao` (por `perm:sales:all:read`)

**Respuesta esperada:** `200` — Sin `unit_cost_snapshot`, `cost_total`, `cost_known`, `gross_margin_amount` ni `gross_margin_percentage`

## 2. Consultar la venta V2 como SuperAdmin (con costo y margen)

Paso `V-06.supervisor` · usuario **`admin.sio`** · ítems de la FASE 10: 16

```http
GET http://127.0.0.1:8108/api/v1/companies/<EMPRESA_A>/sales/<VENTA_2>
```

**Permiso que exige la URL:** `perm:sales:sales:read` + `perm:sales:sales:read-profitability`

- ✅ **Pueden:** `admin.sio` (por `perm:all:all:all`), `admin.dao` (por `perm:sales:all:all`)

**Respuesta esperada:** `200` — `cost_total` = `21600.00`, `gross_margin_amount` = `8400.00`
