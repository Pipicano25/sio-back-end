# Paso 07 de 12 — Permisos: el vendedor no compra

Ejercicio 7 — Seguridad entre empresas y permisos · [Orden del ejercicio](ORDEN.md)

---

## 1. ventas.test intenta registrar una compra en A

Paso `S-01` · usuario **`ventas.test`** · ítems de la FASE 10: 21

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
