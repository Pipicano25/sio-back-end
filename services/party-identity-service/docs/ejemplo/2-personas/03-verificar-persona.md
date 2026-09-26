# Paso 03 de 04 — Marcar la persona como verificada

Ejercicio 2 — Personas: registrar, validar, verificar e inactivar · [← Paso anterior](02-registrar-persona.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](04-inactivar-persona.md)

**Objetivo:** Modificar con control de versión.

**Necesita (de pasos anteriores):** `<PERSONA_ANA>`, `<PAIS_CO>` — pasos [01](01-consultar-pais.md), [02](02-registrar-persona.md)

---

## 1. Cambiar `verification_status` a `VERIFIED`

```http
PUT /api/v1/person-identities/<PERSONA_ANA>
```

```json
{
  "identification_country_id": "<PAIS_CO>",
  "identification_type": "CC",
  "identification_number": "1000000001",
  "first_name": "ANA",
  "middle_name": "MARIA",
  "last_name": "EJEMPLO",
  "second_last_name": "FICTICIA",
  "birth_date": "1990-05-10",
  "verification_status": "VERIFIED",
  "version": 1
}
```

**Permiso que exige la URL:** `perm:party-identity:person_identities:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `party-identity` solo tienen `read`; les falta `update`; `inventario.test` — no tiene ningún permiso sobre `party-identity`

**Por qué se hace así**

- El `PUT` envía la persona completa y la `version` leída (1).
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

## 2. Repetir el cambio con la versión vieja (rechazado)

```http
PUT /api/v1/person-identities/<PERSONA_ANA>
```

```json
{
  "identification_country_id": "<PAIS_CO>",
  "identification_type": "CC",
  "identification_number": "1000000001",
  "first_name": "ANA",
  "middle_name": "MARIA",
  "last_name": "EJEMPLO",
  "second_last_name": "FICTICIA",
  "birth_date": "1990-05-10",
  "verification_status": "VERIFIED",
  "version": 1
}
```

**Permiso que exige la URL:** `perm:party-identity:person_identities:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `party-identity` solo tienen `read`; les falta `update`; `inventario.test` — no tiene ningún permiso sobre `party-identity`

**Por qué se hace así**

- La persona ya está en la versión 2: responde `409 VERSION_CONFLICT` y no cambia nada.

**Respuesta esperada (error) — `409 Conflict`** (abreviada)

```json
{
  "status": 409,
  "code": "PARTY_IDENTITY.VERSION_CONFLICT"
}
```

---

[← Paso anterior](02-registrar-persona.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](04-inactivar-persona.md)
