# Paso 04 de 04 — Desbloquear e inactivar

Ejercicio 3 — Proveedores, bloqueo y desbloqueo · [← Paso anterior](03-bloquear.md) · [Orden del ejercicio](ORDEN.md)

**Objetivo:** Desbloquear, inactivar el segundo proveedor y consultar.

**Necesita (de pasos anteriores):** `<PROVEEDOR>`, `<PROVEEDOR_2>`, `<EMPRESA>` — pasos [01](01-consultar-organizaciones.md), [02](02-seleccionar-proveedores.md)

---

## 1. Desbloquear el laboratorio

```http
POST /api/v1/company-suppliers/<PROVEEDOR>/unblock
```

```json
{
  "version": 3
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_suppliers:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `company_suppliers` solo tienen `read`; les falta `update`; `inventario.test` — no tiene ningún permiso sobre `company_suppliers` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- Desbloquear exige `update`, vuelve a validar la organización y borra el motivo.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "id": "<PROVEEDOR>",
  "organization_identity_id": "<ORG_PROVEEDOR>",
  "internal_code": "PRV-0001",
  "display_name": "Laboratorio Norte (ficticio)",
  "status": "ACTIVE",
  "block_reason": null,
  "version": 4
}
```

## 2. Inactivar la importadora como proveedor

```http
POST /api/v1/company-suppliers/<PROVEEDOR_2>/deactivate
```

```json
{
  "version": 1
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_suppliers:delete`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`)
- ❌ **No pueden (responde `403`):** `supervisor.test` — sobre `company_suppliers` solo tiene `create`, `read`, `update`; le falta `delete`; `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `company_suppliers` solo tienen `read`; les falta `delete`; `inventario.test` — no tiene ningún permiso sobre `company_suppliers` de `commercial-relationship`
- ℹ️ Inactivar **y bloquear** un proveedor exigen `delete` (DS-16); reactivar y desbloquear exigen `update`. `supervisor.test` no puede bloquear.
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- Inactivar el proveedor no afecta su relación como cliente.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "id": "<PROVEEDOR_2>",
  "status": "INACTIVE",
  "version": 2
}
```

## 3. Listar todos los proveedores

```http
GET /api/v1/companies/<EMPRESA>/company-suppliers?status=ALL
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_suppliers:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:commercial-relationship:company_suppliers:read`), `ventas.test` (por `perm:commercial-relationship:company_suppliers:read`), `reportes.test` (por `perm:commercial-relationship:company_suppliers:read`), `consulta.test` (por `perm:commercial-relationship:company_suppliers:read`)
- ❌ **No pueden (responde `403`):** `inventario.test` — no tiene ningún permiso sobre `company_suppliers` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- `status=ALL` incluye `INACTIVE` y `BLOCKED`; sin `status` solo `ACTIVE`.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "internal_code": "PRV-0002",
      "status": "INACTIVE"
    },
    {
      "internal_code": "PRV-0001",
      "status": "ACTIVE"
    }
  ],
  "total_records": 2
}
```

---

[← Paso anterior](03-bloquear.md) · [Orden del ejercicio](ORDEN.md)
