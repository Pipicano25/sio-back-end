# Paso 08 de 12 — Permisos: el comprador no vende

Ejercicio 7 — Seguridad entre empresas y permisos · [Orden del ejercicio](ORDEN.md)

---

## 1. compras.test intenta registrar una venta en A

Paso `S-02` · usuario **`compras.test`** · ítems de la FASE 10: 21

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
