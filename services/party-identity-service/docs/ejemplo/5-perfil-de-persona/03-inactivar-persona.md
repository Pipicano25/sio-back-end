# Paso 03 de 03 — Inactivar la persona

Ejercicio 5 — Perfil de contacto de una persona: cliente persona natural e inactivación · [← Paso anterior](02-registrar-persona-y-perfil.md) · [Orden del ejercicio](ORDEN.md)

**Objetivo:** Ver el efecto sobre el perfil.

**Necesita (de pasos anteriores):** `<PERSONA_CLIENTE>`, `<EMPRESA>` — pasos [01](01-consultar-referencias.md), [02](02-registrar-persona-y-perfil.md)

---

## 1. Inactivar la persona

```http
POST /api/v1/person-identities/<PERSONA_CLIENTE>/deactivate
```

**Permiso que exige la URL:** `perm:party-identity:person_identities:delete`

- ✅ **Pueden:** `admin.sio` (por `perm:all:all:all`)
- ❌ **No pueden (responde `403`):** `admin.dao`, `operario.dao` — sobre `party-identity` solo tienen `create`, `read`, `update`; les falta `delete`
- ℹ️ Inactivar (`POST .../deactivate`) exige `delete`, aunque no elimina; reactivar (`POST .../reactivate`) exige `update`.

**Por qué se hace así**

- Sin cuerpo: inactivar no exige `version` (constitución 4.0.0, D10).
- Exige `delete` sobre `person_identities`; no elimina.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "id": "<PERSONA_CLIENTE>",
  "status": "INACTIVE",
  "version": 2
}
```

## 2. Intentar una versión nueva del perfil (rechazado)

```http
POST /api/v1/person-identities/<PERSONA_CLIENTE>/contact-profile
```

```json
{
  "email": "luis.cliente@correo-ficticio.co",
  "phone": "+57 300 555 0155",
  "confirmed_by_company_id": "<EMPRESA>",
  "version": 1
}
```

**Permiso que exige la URL:** `perm:party-identity:person_contact_profiles:create`

- ✅ **Pueden:** `admin.sio` (por `perm:all:all:all`), `admin.dao` (por `perm:party-identity:all:create`), `operario.dao` (por `perm:party-identity:person_contact_profiles:create`)
- ℹ️ Igual que en organizaciones: se exige membresía `ACTIVE` en la empresa desde la que se confirma, sin permisos de Operational Context.

**Por qué se hace así**

- La persona está `INACTIVE`: `422 PERSON_IDENTITY_INACTIVE`.

**Respuesta esperada (error) — `422 Unprocessable Content`** (abreviada)

```json
{
  "status": 422,
  "code": "PARTY_IDENTITY.PERSON_IDENTITY_INACTIVE"
}
```

## 3. Consultar el perfil (sigue vigente)

```http
GET /api/v1/person-identities/<PERSONA_CLIENTE>/contact-profile
```

**Permiso que exige la URL:** `perm:party-identity:person_contact_profiles:read`

- ✅ **Pueden:** `admin.sio` (por `perm:all:all:all`), `admin.dao` (por `perm:party-identity:all:read`), `operario.dao` (por `perm:party-identity:person_contact_profiles:read`)

**Por qué se hace así**

- Sin cascadas: el perfil vigente se conserva y sigue consultable.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "id": "<id generado>",
  "email": "luis.cliente@correo-ficticio.co",
  "phone": "+57 300 555 0105",
  "is_active": true,
  "confirmed_by_company_id": "<EMPRESA>",
  "confirmed_by_user_id": "<id generado>",
  "version": 1
}
```

---

[← Paso anterior](02-registrar-persona-y-perfil.md) · [Orden del ejercicio](ORDEN.md)
