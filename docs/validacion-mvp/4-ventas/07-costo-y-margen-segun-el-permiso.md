# Paso 07 de 08 — Costo y margen según el permiso

Ejercicio 4 — Ventas con precio por presentación (lista indicada y predeterminada), rechazos, costo FIFO y margen · [Orden del ejercicio](ORDEN.md)

---

## 1. Consultar la venta V2 como vendedor (sin costo ni margen)

Paso `V-06.vendedor` · usuario **`ventas.test`** · ítems de la FASE 10: 16

```http
GET http://127.0.0.1:8108/api/v1/companies/<EMPRESA_A>/sales/<VENTA_2>
```

**Permiso que exige la URL:** `perm:sales:sales:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `ventas.test` (por `perm:sales:all:read`), `supervisor.test` (por `perm:all:all:read`), `consulta.test` (por `perm:sales:sales:read`), `reportes.test` (por `perm:sales:sales:read`)

**Respuesta esperada:** `200` — Sin `unit_cost_snapshot`, `cost_total`, `cost_known`, `gross_margin_amount` ni `gross_margin_percentage`

## 2. Consultar la venta V2 como supervisor (con costo y margen)

Paso `V-06.supervisor` · usuario **`supervisor.test`** · ítems de la FASE 10: 16

```http
GET http://127.0.0.1:8108/api/v1/companies/<EMPRESA_A>/sales/<VENTA_2>
```

**Permiso que exige la URL:** `perm:sales:sales:read` + `perm:sales:sales:read-profitability`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`, `perm:sales:sales:read-profitability`)

**Respuesta esperada:** `200` — `cost_total` = `21600.00`, `gross_margin_amount` = `8400.00`
