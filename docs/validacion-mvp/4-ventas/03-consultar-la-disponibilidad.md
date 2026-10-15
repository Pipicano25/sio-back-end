# Paso 03 de 09 — Consultar la disponibilidad

Ejercicio 4 — Ventas con precio por presentación (lista indicada y predeterminada), rechazos, costo FIFO y margen · [Orden del ejercicio](ORDEN.md)

---

## 1. Consultar la disponibilidad de la venta V2

Paso `V-02.V2` · usuario **`ventas.test`** · ítems de la FASE 10: 14

```http
GET http://127.0.0.1:8108/api/v1/companies/<EMPRESA_A>/sales/<VENTA_2>/availability
```

**Permiso que exige la URL:** `perm:sales:sales:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `ventas.test` (por `perm:sales:all:read`), `supervisor.test` (por `perm:all:all:read`), `consulta.test` (por `perm:sales:sales:read`), `reportes.test` (por `perm:sales:sales:read`)

**Respuesta esperada:** `200` — `all_available` = `true`

## 2. Consultar la disponibilidad de la venta V4

Paso `V-02.V4` · usuario **`ventas.test`** · ítems de la FASE 10: 14

```http
GET http://127.0.0.1:8108/api/v1/companies/<EMPRESA_A>/sales/<VENTA_4>/availability
```

**Permiso que exige la URL:** `perm:sales:sales:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `ventas.test` (por `perm:sales:all:read`), `supervisor.test` (por `perm:all:all:read`), `consulta.test` (por `perm:sales:sales:read`), `reportes.test` (por `perm:sales:sales:read`)

**Respuesta esperada:** `200` — `all_available` = `false`
