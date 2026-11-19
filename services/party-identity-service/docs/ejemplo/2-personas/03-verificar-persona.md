# Paso 03 de 04 — Marcar la persona como verificada

Ejercicio 2 — Personas: registrar, validar, verificar e inactivar · [← Paso anterior](02-registrar-persona.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](04-inactivar-persona.md)

**Objetivo:** Modificar solo el campo que cambia.

**Necesita (de pasos anteriores):** `<PERSONA_ANA>` — pasos [02](02-registrar-persona.md)

---

## 1. Cambiar `verification_status` a `VERIFIED`

```http
PUT /api/v1/person-identities/<PERSONA_ANA>
```

```json
{
  "verification_status": "VERIFIED"
}
```

**Permiso que exige la URL:** `perm:party-identity:person_identities:update`

- ✅ **Pueden:** `admin.sio` (por `perm:all:all:all`), `admin.dao` (por `perm:party-identity:all:update`), `operario.dao` (por `perm:party-identity:person_identities:update`)

**Por qué se hace así**

- El `PUT` es parcial: solo se envía el campo que cambia. Lo demás queda igual.
- `version` es opcional; aquí no se envía y el cambio se aplica sobre la versión vigente.
- Como no cambian país, tipo ni número, **no** se consulta Geography: la modificación funciona aunque Geography no esté disponible (DS-06).
- Si el cuerpo fuera idéntico al actual, respondería `200` sin cambiar la versión.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "id": "<PERSONA_ANA>",
  "identification_type": "CC",
  "identification_number": "1000000001",
  "first_name": "ANA",
  "last_name": "EJEMPLO",
  "verification_status": "VERIFIED",
  "status": "ACTIVE",
  "version": 2
}
```

## 2. Enviar una versión vieja (rechazado)

```http
PUT /api/v1/person-identities/<PERSONA_ANA>
```

```json
{
  "verification_status": "VERIFIED",
  "version": 1
}
```

**Permiso que exige la URL:** `perm:party-identity:person_identities:update`

- ✅ **Pueden:** `admin.sio` (por `perm:all:all:all`), `admin.dao` (por `perm:party-identity:all:update`), `operario.dao` (por `perm:party-identity:person_identities:update`)

**Por qué se hace así**

- Si se envía `version` y no coincide (la persona ya está en la 2), responde `409 VERSION_CONFLICT` y no cambia nada.

**Respuesta esperada (error) — `409 Conflict`** (abreviada)

```json
{
  "status": 409,
  "code": "PARTY_IDENTITY.VERSION_CONFLICT"
}
```

---

[← Paso anterior](02-registrar-persona.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](04-inactivar-persona.md)
