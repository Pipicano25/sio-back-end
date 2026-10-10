# Paso 03 de 06 — Incorporar el cliente

Ejercicio 2 — Relación comercial y precios: proveedor, cliente, productos, adopción, presentaciones y listas · [Orden del ejercicio](ORDEN.md)

---

## 1. Incorporar el cliente persona de la empresa A

Paso `C-09.cliente` · usuario **`admin.test`** · ítems de la FASE 10: 5

```http
POST http://127.0.0.1:8106/api/v1/companies/<EMPRESA_A>/company-customers
```

```json
{
  "customer_kind": "PERSON",
  "person_identity_id": "<PERSONA_CLIENTE>",
  "internal_code": "CLI-<RUN_ID>",
  "display_name": "Cliente MVP <RUN_ID> (dato ficticio)"
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_customers:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)

**Respuesta esperada:** `201`

**Guardar:** `id` → `<CLIENTE>`

**Auditoría que deja:** `CREATE_COMPANY_CUSTOMER` (commercial-relationship)
