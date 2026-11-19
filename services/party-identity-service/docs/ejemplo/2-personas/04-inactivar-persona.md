# Paso 04 de 04 — Inactivar la persona

Ejercicio 2 — Personas: registrar, validar, verificar e inactivar · [← Paso anterior](03-verificar-persona.md) · [Orden del ejercicio](ORDEN.md)

**Objetivo:** Retirarla de uso sin borrarla y consultarla con filtro explícito.

**Necesita (de pasos anteriores):** `<PERSONA_ANA>` — pasos [02](02-registrar-persona.md)

---

## 1. Inactivar a ANA MARIA

```http
POST /api/v1/person-identities/<PERSONA_ANA>/deactivate
```

**Permiso que exige la URL:** `perm:party-identity:person_identities:delete`

- ✅ **Pueden:** `admin.sio` (por `perm:all:all:all`)
- ❌ **No pueden (responde `403`):** `admin.dao`, `operario.dao` — sobre `party-identity` solo tienen `create`, `read`, `update`; les falta `delete`
- ℹ️ Inactivar (`POST .../deactivate`) exige `delete`, aunque no elimina; reactivar (`POST .../reactivate`) exige `update`.

**Por qué se hace así**

- Sin cuerpo: inactivar no exige `version` (constitución 4.0.0, D10).
- Inactivar exige `delete` sobre `person_identities`; reactivar (`/reactivate`) exige `update`.
- `verification_status` sigue `VERIFIED`: son estados independientes.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "id": "<PERSONA_ANA>",
  "verification_status": "VERIFIED",
  "status": "INACTIVE",
  "version": 3
}
```

## 2. Listar personas (por defecto solo `ACTIVE`)

```http
GET /api/v1/person-identities
```

**Permiso que exige la URL:** `perm:party-identity:person_identities:read`

- ✅ **Pueden:** `admin.sio` (por `perm:all:all:all`), `admin.dao` (por `perm:party-identity:all:read`), `operario.dao` (por `perm:party-identity:person_identities:read`)

**Por qué se hace así**

- Sin filtro de estado la lista muestra solo personas activas: ANA MARIA ya no aparece.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "total_records": 0
}
```

## 3. Listar personas inactivas

```http
GET /api/v1/person-identities?status=INACTIVE
```

**Permiso que exige la URL:** `perm:party-identity:person_identities:read`

- ✅ **Pueden:** `admin.sio` (por `perm:all:all:all`), `admin.dao` (por `perm:party-identity:all:read`), `operario.dao` (por `perm:party-identity:person_identities:read`)

**Por qué se hace así**

- Las inactivas se consultan con `status=INACTIVE`. Por `id` se devuelve en cualquier estado.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "id": "<PERSONA_ANA>",
      "status": "INACTIVE"
    }
  ],
  "total_records": 1
}
```

---

[← Paso anterior](03-verificar-persona.md) · [Orden del ejercicio](ORDEN.md)
