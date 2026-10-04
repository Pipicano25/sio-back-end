# Paso 03 de 04 — Bloquear el proveedor

Ejercicio 3 — Proveedores, bloqueo y desbloqueo · [← Paso anterior](02-seleccionar-proveedores.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](04-desbloquear-y-consultar.md)

**Objetivo:** Bloquear con motivo y ver las transiciones válidas.

**Necesita (de pasos anteriores):** `<PROVEEDOR>` — pasos [02](02-seleccionar-proveedores.md)

---

## 1. Bloquear el laboratorio

```http
POST /api/v1/company-suppliers/<PROVEEDOR>/block
```

```json
{
  "block_reason": "Incumplimiento de entregas (ficticio)",
  "version": 1
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_suppliers:delete`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`)
- ❌ **No pueden (responde `403`):** `supervisor.test` — sobre `company_suppliers` solo tiene `create`, `read`, `update`; le falta `delete`; `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `company_suppliers` solo tienen `read`; les falta `delete`; `inventario.test` — no tiene ningún permiso sobre `company_suppliers` de `commercial-relationship`
- ℹ️ Inactivar **y bloquear** un proveedor exigen `delete` (DS-16); reactivar y desbloquear exigen `update`. `supervisor.test` no puede bloquear.
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- Bloquear exige `delete` y un motivo de 1 a 500 caracteres. No consulta Party Identity.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "id": "<PROVEEDOR>",
  "organization_identity_id": "<ORG_PROVEEDOR>",
  "internal_code": "PRV-0001",
  "display_name": "Laboratorio (ficticio)",
  "status": "BLOCKED",
  "block_reason": "Incumplimiento de entregas (ficticio)",
  "version": 2
}
```

## 2. Reactivar el proveedor bloqueado (rechazado)

```http
POST /api/v1/company-suppliers/<PROVEEDOR>/reactivate
```

```json
{
  "version": 2
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_suppliers:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `company_suppliers` solo tienen `read`; les falta `update`; `inventario.test` — no tiene ningún permiso sobre `company_suppliers` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- De `BLOCKED` solo se sale desbloqueando: `409 INVALID_STATUS_TRANSITION`.

**Respuesta esperada (error) — `409 Conflict`** (abreviada)

```json
{
  "status": 409,
  "code": "COMMERCIAL_RELATIONSHIP.INVALID_STATUS_TRANSITION",
  "detail": "La acción reactivate no es válida desde el estado BLOCKED."
}
```

## 3. Corregir el nombre visible sin desbloquear

```http
PUT /api/v1/company-suppliers/<PROVEEDOR>
```

```json
{
  "internal_code": "PRV-0001",
  "display_name": "Laboratorio Norte (ficticio)",
  "preferred_contact_person_id": null,
  "version": 2
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_suppliers:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `company_suppliers` solo tienen `read`; les falta `update`; `inventario.test` — no tiene ningún permiso sobre `company_suppliers` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- El `PUT` se permite sobre un proveedor `BLOCKED` y no cambia ni el estado ni el motivo (DS-17).

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "id": "<PROVEEDOR>",
  "display_name": "Laboratorio Norte (ficticio)",
  "status": "BLOCKED",
  "block_reason": "Incumplimiento de entregas (ficticio)",
  "version": 3
}
```

---

[← Paso anterior](02-seleccionar-proveedores.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](04-desbloquear-y-consultar.md)
