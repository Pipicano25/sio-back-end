# Paso 09 de 12 — Permisos: consulta no escribe

Ejercicio 7 — Seguridad entre empresas y permisos · [Orden del ejercicio](ORDEN.md)

---

## 1. consulta.test intenta registrar una compra en A

Paso `S-03.compra` · usuario **`consulta.test`** · ítems de la FASE 10: 21

```http
POST http://127.0.0.1:8107/api/v1/companies/<EMPRESA_A>/purchases
```

```json
{
  "branch_id": "<SUCURSAL_A1>",
  "company_supplier_id": "<PROVEEDOR>",
  "operation_date": "<FECHA_NEGOCIO>",
  "lines": [
    {
      "company_product_id": "<PRODUCTO_EMPRESA_A>",
      "quantity": "1",
      "unit_cost": "1000"
    }
  ]
}
```

**Permiso que exige la URL:** `perm:purchase:purchases:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `compras.test` (por `perm:purchase:all:all`), `supervisor.test` (por `perm:all:all:create`)

**Respuesta esperada:** `403`

## 2. consulta.test intenta registrar una venta en A

Paso `S-03.venta` · usuario **`consulta.test`** · ítems de la FASE 10: 21

```http
POST http://127.0.0.1:8108/api/v1/companies/<EMPRESA_A>/sales
```

```json
{
  "branch_id": "<SUCURSAL_A1>",
  "company_customer_id": "<CLIENTE>",
  "lines": [
    {
      "company_product_id": "<PRODUCTO_EMPRESA_A>",
      "quantity": "1"
    }
  ]
}
```

**Permiso que exige la URL:** `perm:sales:sales:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `ventas.test` (por `perm:sales:all:create`), `supervisor.test` (por `perm:all:all:create`)

**Respuesta esperada:** `403`
