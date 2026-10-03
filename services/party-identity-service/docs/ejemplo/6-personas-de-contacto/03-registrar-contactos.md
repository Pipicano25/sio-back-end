# Paso 03 de 04 — Registrar contactos

Ejercicio 6 — Personas de contacto: principal, set-primary e inactivación · [← Paso anterior](02-registrar-identidades.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](04-set-primary-e-inactivar.md)

**Objetivo:** Crear el principal y el de cartera.

**Necesita (de pasos anteriores):** `<ORG_LAB>`, `<PERSONA_MARTA>` — pasos [02](02-registrar-identidades.md)

**Deja guardado para los siguientes pasos:** `<CONTACTO_COMERCIAL>`, `<CONTACTO_CARTERA>`

---

## 1. Registrar el contacto comercial como principal

```http
POST /api/v1/organization-identities/<ORG_LAB>/contact-persons
```

```json
{
  "person_identity_id": "<PERSONA_MARTA>",
  "position": "Comercial",
  "is_primary": true
}
```

**Permiso que exige la URL:** `perm:party-identity:organization_contact_persons:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test` — sobre `party-identity` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `party-identity`; `reportes.test`, `consulta.test` — tienen permisos sobre `party-identity`, pero ninguno sobre `organization_contact_persons`

**Por qué se hace así**

- Vincula una `PersonIdentity`; con ella no hace falta correo ni teléfono.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<CONTACTO_COMERCIAL>",
  "organization_identity_id": "<ORG_LAB>",
  "person_identity_id": "<PERSONA_MARTA>",
  "position": "Comercial",
  "phone": null,
  "is_primary": true,
  "is_active": true,
  "version": 1
}
```

**Guardar:** `id` → `<CONTACTO_COMERCIAL>`

## 2. Registrar el contacto de cartera

```http
POST /api/v1/organization-identities/<ORG_LAB>/contact-persons
```

```json
{
  "position": "Cartera",
  "phone": "+57 601 555 0166"
}
```

**Permiso que exige la URL:** `perm:party-identity:organization_contact_persons:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test` — sobre `party-identity` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `party-identity`; `reportes.test`, `consulta.test` — tienen permisos sobre `party-identity`, pero ninguno sobre `organization_contact_persons`

**Por qué se hace así**

- Contacto sin persona vinculada: basta un medio de contacto (aquí el teléfono).
- Se crea como no principal (`is_primary` por defecto `false`): ya hay un principal y solo puede haber uno.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<CONTACTO_CARTERA>",
  "organization_identity_id": "<ORG_LAB>",
  "person_identity_id": null,
  "position": "Cartera",
  "phone": "+57 601 555 0166",
  "is_primary": false,
  "is_active": true,
  "version": 1
}
```

**Guardar:** `id` → `<CONTACTO_CARTERA>`

## 3. Intentar crear un segundo principal (rechazado)

```http
POST /api/v1/organization-identities/<ORG_LAB>/contact-persons
```

```json
{
  "position": "Logística",
  "phone": "+57 601 555 0167",
  "is_primary": true
}
```

**Permiso que exige la URL:** `perm:party-identity:organization_contact_persons:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test` — sobre `party-identity` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `party-identity`; `reportes.test`, `consulta.test` — tienen permisos sobre `party-identity`, pero ninguno sobre `organization_contact_persons`

**Por qué se hace así**

- Ya hay un principal: `409 PRIMARY_CONTACT_CONFLICT`. Para cambiarlo se usa `set-primary`.

**Respuesta esperada (error) — `409 Conflict`** (abreviada)

```json
{
  "status": 409,
  "code": "PARTY_IDENTITY.PRIMARY_CONTACT_CONFLICT"
}
```

---

[← Paso anterior](02-registrar-identidades.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](04-set-primary-e-inactivar.md)
