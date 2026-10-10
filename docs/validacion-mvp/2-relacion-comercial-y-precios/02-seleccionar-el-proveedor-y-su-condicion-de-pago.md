# Paso 02 de 06 — Seleccionar el proveedor y su condición de pago

Ejercicio 2 — Relación comercial y precios: proveedor, cliente, productos, adopción, presentaciones y listas · [Orden del ejercicio](ORDEN.md)

---

## 1. Seleccionar el proveedor de la empresa A

Paso `C-08.proveedor` · usuario **`admin.test`** · ítems de la FASE 10: 4

```http
POST http://127.0.0.1:8106/api/v1/companies/<EMPRESA_A>/company-suppliers
```

```json
{
  "organization_identity_id": "<ORG_PROVEEDOR>",
  "internal_code": "PRV-<RUN_ID>",
  "display_name": "Proveedor MVP <RUN_ID> (dato ficticio)"
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_suppliers:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)

**Respuesta esperada:** `201`

**Guardar:** `id` → `<PROVEEDOR>`

**Auditoría que deja:** `CREATE_COMPANY_SUPPLIER` (commercial-relationship)

## 2. Registrar la condición de pago a crédito del proveedor

Paso `C-08.condicion` · usuario **`admin.test`** · ítems de la FASE 10: 4

```http
POST http://127.0.0.1:8106/api/v1/companies/<EMPRESA_A>/supplier-payment-conditions
```

```json
{
  "company_supplier_id": "<PROVEEDOR>",
  "payment_condition_type_id": "<TIPO_CREDITO>",
  "currency_code": "COP",
  "payment_terms_days": 30,
  "is_default": true
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:supplier_payment_conditions:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)

**Por qué se hace así**

- El tipo CREDIT de Payment Reference exige plazo mayor que 0.

**Respuesta esperada:** `201`

**Guardar:** `id` → `<CONDICION_CREDITO>`

**Auditoría que deja:** `CREATE_SUPPLIER_PAYMENT_CONDITION` (commercial-relationship)
