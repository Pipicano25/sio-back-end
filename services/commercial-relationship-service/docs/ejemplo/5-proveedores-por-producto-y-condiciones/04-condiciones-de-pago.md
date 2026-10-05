# Paso 04 de 04 — Registrar las condiciones de pago

Ejercicio 5 — Proveedores por producto y condiciones de pago · [← Paso anterior](03-productos-de-proveedor.md) · [Orden del ejercicio](ORDEN.md)

**Objetivo:** Contado con plazo (rechazado) y crédito predeterminado.

**Necesita (de pasos anteriores):** `<EMPRESA>`, `<PROVEEDOR>`, `<TIPO_CASH>`, `<TIPO_CREDIT>` — pasos [01](01-consultar-datos.md), [02](02-preparar.md)

---

## 1. Registrar contado con 15 días (rechazado)

```http
POST /api/v1/companies/<EMPRESA>/supplier-payment-conditions
```

```json
{
  "company_supplier_id": "<PROVEEDOR>",
  "payment_condition_type_id": "<TIPO_CASH>",
  "currency_code": "COP",
  "payment_terms_days": 15
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:supplier_payment_conditions:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `supplier_payment_conditions` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `supplier_payment_conditions` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- Contado exige 0 días: `422 PAYMENT_TERMS_INCONSISTENT` (FR-033).

**Respuesta esperada (error) — `422 Unprocessable Content`** (abreviada)

```json
{
  "status": 422,
  "code": "COMMERCIAL_RELATIONSHIP.PAYMENT_TERMS_INCONSISTENT",
  "detail": "Una condición de contado exige un plazo de 0 días.",
  "errors": [
    {
      "field": "payment_terms_days",
      "message": "Una condición de contado exige un plazo de 0 días.",
      "code": "PAYMENT_TERMS_INCONSISTENT"
    }
  ]
}
```

## 2. Registrar contado con descuento por pronto pago

```http
POST /api/v1/companies/<EMPRESA>/supplier-payment-conditions
```

```json
{
  "company_supplier_id": "<PROVEEDOR>",
  "payment_condition_type_id": "<TIPO_CASH>",
  "currency_code": "COP",
  "payment_terms_days": 0,
  "cash_discount_percentage": "2.5"
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:supplier_payment_conditions:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `supplier_payment_conditions` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `supplier_payment_conditions` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- Plazo 0 y descuento entre 0 y 100 con hasta 4 decimales.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<id generado>",
  "company_supplier_id": "<PROVEEDOR>",
  "payment_condition_type_id": "<TIPO_CASH>",
  "currency_code": "COP",
  "payment_terms_days": 0,
  "credit_limit": null,
  "cash_discount_percentage": "2.5000",
  "is_default": false,
  "status": "ACTIVE",
  "version": 1
}
```

## 3. Registrar crédito a 30 días como predeterminado en COP

```http
POST /api/v1/companies/<EMPRESA>/supplier-payment-conditions
```

```json
{
  "company_supplier_id": "<PROVEEDOR>",
  "payment_condition_type_id": "<TIPO_CREDIT>",
  "currency_code": "COP",
  "payment_terms_days": 30,
  "credit_limit": "5000000.00",
  "is_default": true
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:supplier_payment_conditions:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `supplier_payment_conditions` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `supplier_payment_conditions` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- Una condición de crédito no crea deuda; la deuda nace en Finanzas con una compra confirmada. Hay como máximo una predeterminada por proveedor y moneda.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<id generado>",
  "company_supplier_id": "<PROVEEDOR>",
  "payment_condition_type_id": "<TIPO_CREDIT>",
  "currency_code": "COP",
  "payment_terms_days": 30,
  "credit_limit": "5000000.00",
  "cash_discount_percentage": null,
  "is_default": true,
  "status": "ACTIVE",
  "version": 1
}
```

---

[← Paso anterior](03-productos-de-proveedor.md) · [Orden del ejercicio](ORDEN.md)
