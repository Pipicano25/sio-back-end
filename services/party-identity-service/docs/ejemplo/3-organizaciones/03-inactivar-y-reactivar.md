# Paso 03 de 03 — Inactivar y reactivar

Ejercicio 3 — Organizaciones: registrar, rechazos, inactivar y reactivar · [← Paso anterior](02-registrar-organizacion.md) · [Orden del ejercicio](ORDEN.md)

**Objetivo:** Retirar la organización de uso y volver a activarla.

**Necesita (de pasos anteriores):** `<ORG_EJEMPLO>` — pasos [02](02-registrar-organizacion.md)

---

## 1. Inactivar la organización

```http
POST /api/v1/organization-identities/<ORG_EJEMPLO>/deactivate
```

```json
{
  "version": 1
}
```

**Permiso que exige la URL:** `perm:party-identity:organization_identities:delete`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`)
- ❌ **No pueden (responde `403`):** `supervisor.test` — sobre `party-identity` solo tiene `create`, `read`, `update`; le falta `delete`; `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `party-identity` solo tienen `read`; les falta `delete`; `inventario.test` — no tiene ningún permiso sobre `party-identity`
- ℹ️ Inactivar exige `delete`; reactivar exige `update`. Por eso `supervisor.test` puede reactivar pero no inactivar.

**Por qué se hace así**

- Exige `delete` sobre `organization_identities`. No se borra: sigue consultable por `id` con `status: INACTIVE`, y los servicios que ya la referencian no se ven afectados.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "id": "<ORG_EJEMPLO>",
  "identification_type": "NIT",
  "identification_number": "900000001-1",
  "legal_name": "COMERCIALIZADORA EJEMPLO FICTICIA S.A.S.",
  "registration_status": "ACTIVA",
  "status": "INACTIVE",
  "version": 2
}
```

## 2. Intentar inactivarla otra vez (rechazado)

```http
POST /api/v1/organization-identities/<ORG_EJEMPLO>/deactivate
```

```json
{
  "version": 2
}
```

**Permiso que exige la URL:** `perm:party-identity:organization_identities:delete`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`)
- ❌ **No pueden (responde `403`):** `supervisor.test` — sobre `party-identity` solo tiene `create`, `read`, `update`; le falta `delete`; `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `party-identity` solo tienen `read`; les falta `delete`; `inventario.test` — no tiene ningún permiso sobre `party-identity`
- ℹ️ Inactivar exige `delete`; reactivar exige `update`. Por eso `supervisor.test` puede reactivar pero no inactivar.

**Por qué se hace así**

- Ya está inactiva: `409 INVALID_STATUS_TRANSITION` y la versión no cambia.

**Respuesta esperada (error) — `409 Conflict`** (abreviada)

```json
{
  "status": 409,
  "code": "PARTY_IDENTITY.INVALID_STATUS_TRANSITION"
}
```

## 3. Reactivar la organización

```http
POST /api/v1/organization-identities/<ORG_EJEMPLO>/reactivate
```

```json
{
  "version": 2
}
```

**Permiso que exige la URL:** `perm:party-identity:organization_identities:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `party-identity` solo tienen `read`; les falta `update`; `inventario.test` — no tiene ningún permiso sobre `party-identity`

**Por qué se hace así**

- Reactivar exige `update`: por eso `supervisor.test` puede reactivar aunque no pueda inactivar.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "id": "<ORG_EJEMPLO>",
  "identification_type": "NIT",
  "identification_number": "900000001-1",
  "legal_name": "COMERCIALIZADORA EJEMPLO FICTICIA S.A.S.",
  "registration_status": "ACTIVA",
  "status": "ACTIVE",
  "version": 3
}
```

## 4. Consultar la organización por `id`

```http
GET /api/v1/organization-identities/<ORG_EJEMPLO>
```

**Permiso que exige la URL:** `perm:party-identity:organization_identities:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:party-identity:organization_identities:read`), `ventas.test` (por `perm:party-identity:organization_identities:read`), `reportes.test` (por `perm:party-identity:organization_identities:read`), `consulta.test` (por `perm:party-identity:organization_identities:read`)
- ❌ **No pueden (responde `403`):** `inventario.test` — no tiene ningún permiso sobre `party-identity`

**Por qué se hace así**

- Es la consulta que usan los demás servicios para validar la referencia (contrato Provider).

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "id": "<ORG_EJEMPLO>",
  "identification_type": "NIT",
  "identification_number": "900000001-1",
  "legal_name": "COMERCIALIZADORA EJEMPLO FICTICIA S.A.S.",
  "registration_status": "ACTIVA",
  "status": "ACTIVE",
  "version": 3
}
```

---

[← Paso anterior](02-registrar-organizacion.md) · [Orden del ejercicio](ORDEN.md)
