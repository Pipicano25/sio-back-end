# Paso 03 de 05 — Registrar los usuarios operativos de la empresa A

Ejercicio 4 — Usuarios operativos de una empresa · [← Paso anterior](02-registrar-empresas.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](04-consultar-usuarios.md)

**Objetivo:** Registrar a la supervisora por `username` y comprobar los rechazos.

**Necesita (de pasos anteriores):** `<EMPRESA_A>`, `<PERSONA_SUPERVISORA>`, `<PERSONA_COMPRADOR>` — pasos [01](01-consultar-personas.md), [02](02-registrar-empresas.md)

**Deja guardado para los siguientes pasos:** `<USR_SUPERVISORA>`, `<USR_COMPRADOR_A>`

---

## 1. Registrar a supervisor.test por nombre de usuario

```http
POST /api/v1/companies/<EMPRESA_A>/application-users
```

```json
{
  "username": "supervisor.test",
  "person_identity_id": "<PERSONA_SUPERVISORA>",
  "display_name": "Supervisora (ficticia)",
  "reference_email": "supervisora@ficticia.co"
}
```

**Permiso que exige la URL:** `perm:operational-context:application_users:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `operational-context` solo tienen `read`; les falta `create`
- ℹ️ Para registrar un usuario operativo el token debe poder leer `person_identities` en Party Identity (el servicio valida la persona con ese token); la cuenta de Keycloak la verifica el servicio con su propia identidad técnica.
- 🔒 Aislamiento por empresa (Fase B): además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa o `platform:administer`; si no, la URL responde `404`, igual que un `id` inexistente.

**Por qué se hace así**

- El servicio busca la cuenta `supervisor.test` en Keycloak (solo lectura, con su propia identidad técnica) y guarda su `sub`; el `username` no se guarda.
- La persona se valida en Party Identity con el token de quien registra.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<USR_SUPERVISORA>",
  "company_id": "<EMPRESA_A>",
  "keycloak_user_id": "supervisor.test",
  "person_identity_id": "<PERSONA_SUPERVISORA>",
  "display_name": "Supervisora (ficticia)",
  "status": "ACTIVE",
  "version": 1
}
```

**Guardar:** `id` → `<USR_SUPERVISORA>`

## 2. Intentar registrarla otra vez (rechazado)

```http
POST /api/v1/companies/<EMPRESA_A>/application-users
```

```json
{
  "username": "supervisor.test",
  "person_identity_id": "<PERSONA_SUPERVISORA>",
  "display_name": "Duplicada"
}
```

**Permiso que exige la URL:** `perm:operational-context:application_users:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `operational-context` solo tienen `read`; les falta `create`
- ℹ️ Para registrar un usuario operativo el token debe poder leer `person_identities` en Party Identity (el servicio valida la persona con ese token); la cuenta de Keycloak la verifica el servicio con su propia identidad técnica.
- 🔒 Aislamiento por empresa (Fase B): además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa o `platform:administer`; si no, la URL responde `404`, igual que un `id` inexistente.

**Por qué se hace así**

- Ya existe una membresía `ACTIVE` de esa persona en la empresa: `409 DUPLICATE_MEMBERSHIP`.

**Respuesta esperada (error) — `409 Conflict`** (abreviada)

```json
{
  "status": 409,
  "code": "OPERATIONAL_CONTEXT.DUPLICATE_MEMBERSHIP",
  "detail": "Ya existe una membresía activa de esa persona en la empresa.",
  "errors": [
    {
      "field": "person_identity_id",
      "message": "Ya existe una membresía activa de esa persona en la empresa.",
      "code": "DUPLICATE_MEMBERSHIP"
    }
  ]
}
```

## 3. Intentar registrar una cuenta técnica (rechazado)

```http
POST /api/v1/companies/<EMPRESA_A>/application-users
```

```json
{
  "keycloak_user_id": "service-account-inventory-service",
  "person_identity_id": "<PERSONA_COMPRADOR>",
  "display_name": "Servicio"
}
```

**Permiso que exige la URL:** `perm:operational-context:application_users:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `operational-context` solo tienen `read`; les falta `create`
- ℹ️ Para registrar un usuario operativo el token debe poder leer `person_identities` en Party Identity (el servicio valida la persona con ese token); la cuenta de Keycloak la verifica el servicio con su propia identidad técnica.
- 🔒 Aislamiento por empresa (Fase B): además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa o `platform:administer`; si no, la URL responde `404`, igual que un `id` inexistente.

**Por qué se hace así**

- Las cuentas de servicio (`client_credentials`) no son usuarios operativos: `422 TECHNICAL_ACCOUNT_NOT_ALLOWED` (FR-019).

**Respuesta esperada (error) — `422 Unprocessable Content`** (abreviada)

```json
{
  "status": 422,
  "code": "OPERATIONAL_CONTEXT.TECHNICAL_ACCOUNT_NOT_ALLOWED",
  "detail": "La cuenta indicada es la cuenta de servicio de un cliente técnico y no puede registrarse como usuario operativo."
}
```

## 4. Registrar a compras.test

```http
POST /api/v1/companies/<EMPRESA_A>/application-users
```

```json
{
  "username": "compras.test",
  "person_identity_id": "<PERSONA_COMPRADOR>",
  "display_name": "Comprador (ficticio)"
}
```

**Permiso que exige la URL:** `perm:operational-context:application_users:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `operational-context` solo tienen `read`; les falta `create`
- ℹ️ Para registrar un usuario operativo el token debe poder leer `person_identities` en Party Identity (el servicio valida la persona con ese token); la cuenta de Keycloak la verifica el servicio con su propia identidad técnica.
- 🔒 Aislamiento por empresa (Fase B): además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa o `platform:administer`; si no, la URL responde `404`, igual que un `id` inexistente.

**Por qué se hace así**

- Usuario operativo de solo lectura en Operational Context.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<USR_COMPRADOR_A>",
  "company_id": "<EMPRESA_A>",
  "keycloak_user_id": "compras.test",
  "person_identity_id": "<PERSONA_COMPRADOR>",
  "display_name": "Comprador (ficticio)",
  "status": "ACTIVE",
  "version": 1
}
```

**Guardar:** `id` → `<USR_COMPRADOR_A>`

---

[← Paso anterior](02-registrar-empresas.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](04-consultar-usuarios.md)
