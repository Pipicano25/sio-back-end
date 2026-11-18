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

- ✅ **Pueden:** `admin.sio` (por `perm:all:all:all`), `admin.dao` (por `perm:commercial-relationship:all:update`)
- ❌ **No pueden (responde `403`):** `operario.dao` — sobre `company_suppliers` solo tiene `read`; le falta `update`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.sio`** (DS-03).

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

- ✅ **Pueden:** `admin.sio` (por `perm:all:all:all`), `admin.dao` (por `perm:commercial-relationship:all:delete`)
- ❌ **No pueden (responde `403`):** `operario.dao` — sobre `company_suppliers` solo tiene `read`; le falta `delete`
- ℹ️ Inactivar **y bloquear** un proveedor exigen `delete` (DS-16); reactivar y desbloquear exigen `update`. El operario (`Compras`, `Ventas` e `Inventario`) no puede bloquear.
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.sio`** (DS-03).

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

- ✅ **Pueden:** `admin.sio` (por `perm:all:all:all`), `admin.dao` (por `perm:commercial-relationship:all:read`), `operario.dao` (por `perm:commercial-relationship:company_suppliers:read`)
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.sio`** (DS-03).

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
