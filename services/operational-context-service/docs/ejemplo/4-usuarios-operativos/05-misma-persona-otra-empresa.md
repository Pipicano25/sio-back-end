# Paso 05 de 05 — La misma persona en otra empresa

Ejercicio 4 — Usuarios operativos de una empresa · [← Paso anterior](04-consultar-usuarios.md) · [Orden del ejercicio](ORDEN.md)

**Objetivo:** Registrar a `operario.dao` también en la empresa B y retirarlo solo de esa empresa.

**Necesita (de pasos anteriores):** `<EMPRESA_B>`, `<PERSONA_COMPRADOR>`, `<USR_COMPRADOR_A>` — pasos [01](01-consultar-personas.md), [02](02-registrar-empresas.md), [03](03-registrar-usuarios.md)

**Deja guardado para los siguientes pasos:** `<USR_COMPRADOR_B>`

---

## 1. Registrar a operario.dao en la empresa B

```http
POST /api/v1/companies/<EMPRESA_B>/application-users
```

```json
{
  "username": "operario.dao",
  "person_identity_id": "<PERSONA_COMPRADOR>",
  "display_name": "Comprador (ficticio)"
}
```

**Permiso que exige la URL:** `perm:operational-context:application_users:create`

- ✅ **Pueden:** `admin.sio` (por `perm:all:all:all`), `admin.dao` (por `perm:operational-context:all:create`)
- ❌ **No pueden (responde `403`):** `operario.dao` — sobre `operational-context` solo tiene `read`; le falta `create`
- ℹ️ Para registrar un usuario operativo el token debe poder leer `person_identities` en Party Identity (el servicio valida la persona con ese token); la cuenta de Keycloak la verifica el servicio con su propia identidad técnica.
- 🔒 Aislamiento por empresa (Fase B): además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa o `platform:administer`; si no, la URL responde `404`, igual que un `id` inexistente.

**Por qué se hace así**

- Ni la persona ni la cuenta son únicas globalmente: son dos membresías independientes.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<USR_COMPRADOR_B>",
  "company_id": "<EMPRESA_B>",
  "keycloak_user_id": "operario.dao",
  "person_identity_id": "<PERSONA_COMPRADOR>",
  "display_name": "Comprador (ficticio)",
  "status": "ACTIVE",
  "version": 1
}
```

**Guardar:** `id` → `<USR_COMPRADOR_B>`

## 2. Inactivar la membresía de la empresa B

```http
POST /api/v1/application-users/<USR_COMPRADOR_B>/deactivate
```

```json
{
  "version": 1
}
```

**Permiso que exige la URL:** `perm:operational-context:application_users:delete`

- ✅ **Pueden:** `admin.sio` (por `perm:all:all:all`), `admin.dao` (por `perm:operational-context:all:delete`)
- ❌ **No pueden (responde `403`):** `operario.dao` — sobre `operational-context` solo tiene `read`; le falta `delete`
- 🔒 Aislamiento por empresa (Fase B): además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa o `platform:administer`; si no, la URL responde `404`, igual que un `id` inexistente.

**Por qué se hace así**

- Solo termina la relación con la empresa B: la membresía de A, la cuenta de Keycloak y la `PersonIdentity` no cambian (DS-11).

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "status": "INACTIVE",
  "version": 2
}
```

## 3. Consultar la membresía de la empresa A

```http
GET /api/v1/application-users/<USR_COMPRADOR_A>
```

**Permiso que exige la URL:** `perm:operational-context:application_users:read`

- ✅ **Pueden:** `admin.sio` (por `perm:all:all:all`), `admin.dao` (por `perm:operational-context:all:read`), `operario.dao` (por `perm:operational-context:all:read`)
- 🔒 Aislamiento por empresa (Fase B): además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa o `platform:administer`; si no, la URL responde `404`, igual que un `id` inexistente.

**Por qué se hace así**

- Sigue `ACTIVE`.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "company_id": "<EMPRESA_A>",
  "status": "ACTIVE",
  "version": 1
}
```

## 4. Reactivar la membresía de la empresa B

```http
POST /api/v1/application-users/<USR_COMPRADOR_B>/reactivate
```

```json
{
  "version": 2
}
```

**Permiso que exige la URL:** `perm:operational-context:application_users:update`

- ✅ **Pueden:** `admin.sio` (por `perm:all:all:all`), `admin.dao` (por `perm:operational-context:all:update`)
- ❌ **No pueden (responde `403`):** `operario.dao` — sobre `operational-context` solo tiene `read`; le falta `update`
- 🔒 Aislamiento por empresa (Fase B): además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa o `platform:administer`; si no, la URL responde `404`, igual que un `id` inexistente.

**Por qué se hace así**

- Reactivar vuelve a validar la cuenta en Keycloak y la persona en Party Identity.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "status": "ACTIVE",
  "version": 3
}
```

---

[← Paso anterior](04-consultar-usuarios.md) · [Orden del ejercicio](ORDEN.md)
