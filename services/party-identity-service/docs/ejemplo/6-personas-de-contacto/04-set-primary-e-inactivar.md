# Paso 04 de 04 — Cambiar el principal e inactivar

Ejercicio 6 — Personas de contacto: principal, set-primary e inactivación · [← Paso anterior](03-registrar-contactos.md) · [Orden del ejercicio](ORDEN.md)

**Objetivo:** Usar set-primary y retirar un contacto.

**Necesita (de pasos anteriores):** `<CONTACTO_CARTERA>`, `<CONTACTO_COMERCIAL>`, `<ORG_LAB>` — pasos [02](02-registrar-identidades.md), [03](03-registrar-contactos.md)

---

## 1. Establecer el contacto de cartera como principal

```http
POST /api/v1/organization-contact-persons/<CONTACTO_CARTERA>:set-primary
```

```json
{
  "version": 1
}
```

**Permiso que exige la URL:** `perm:party-identity:organization_contact_persons:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test` — sobre `party-identity` solo tienen `read`; les falta `update`; `inventario.test` — no tiene ningún permiso sobre `party-identity`; `reportes.test`, `consulta.test` — tienen permisos sobre `party-identity`, pero ninguno sobre `organization_contact_persons`
- ℹ️ `:set-primary` y `:reactivate` exigen `update`; `is_primary` no se cambia con `PUT`.

**Por qué se hace así**

- Exige `update`. En una sola operación el comercial deja de ser principal.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "id": "<CONTACTO_CARTERA>",
  "organization_identity_id": "<ORG_LAB>",
  "person_identity_id": null,
  "position": "Cartera",
  "phone": "+57 601 555 0166",
  "is_primary": true,
  "is_active": true,
  "version": 2
}
```

## 2. Consultar el contacto comercial por `id` (contrato Provider)

```http
GET /api/v1/organization-contact-persons/<CONTACTO_COMERCIAL>
```

**Permiso que exige la URL:** `perm:party-identity:organization_contact_persons:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:party-identity:organization_contact_persons:read`), `ventas.test` (por `perm:party-identity:organization_contact_persons:read`)
- ❌ **No pueden (responde `403`):** `inventario.test` — no tiene ningún permiso sobre `party-identity`; `reportes.test`, `consulta.test` — tienen permisos sobre `party-identity`, pero ninguno sobre `organization_contact_persons`

**Por qué se hace así**

- Commercial Relationship comprueba `organization_identity_id` e `is_active` con esta consulta.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "id": "<CONTACTO_COMERCIAL>",
  "organization_identity_id": "<ORG_LAB>",
  "person_identity_id": "<PERSONA_MARTA>",
  "position": "Comercial",
  "phone": null,
  "is_primary": false,
  "is_active": true,
  "version": 2
}
```

## 3. Inactivar el contacto de cartera

```http
POST /api/v1/organization-contact-persons/<CONTACTO_CARTERA>:deactivate
```

```json
{
  "version": 2
}
```

**Permiso que exige la URL:** `perm:party-identity:organization_contact_persons:delete`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`)
- ❌ **No pueden (responde `403`):** `supervisor.test` — sobre `party-identity` solo tiene `create`, `read`, `update`; le falta `delete`; `compras.test`, `ventas.test` — sobre `party-identity` solo tienen `read`; les falta `delete`; `inventario.test` — no tiene ningún permiso sobre `party-identity`; `reportes.test`, `consulta.test` — tienen permisos sobre `party-identity`, pero ninguno sobre `organization_contact_persons`

**Por qué se hace así**

- Exige `delete`; no elimina. Deja de ser principal; la organización queda sin principal.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "id": "<CONTACTO_CARTERA>",
  "organization_identity_id": "<ORG_LAB>",
  "person_identity_id": null,
  "position": "Cartera",
  "phone": "+57 601 555 0166",
  "is_primary": false,
  "is_active": false,
  "version": 3
}
```

## 4. Listar los contactos vigentes

```http
GET /api/v1/organization-identities/<ORG_LAB>/contact-persons
```

**Permiso que exige la URL:** `perm:party-identity:organization_contact_persons:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:party-identity:organization_contact_persons:read`), `ventas.test` (por `perm:party-identity:organization_contact_persons:read`)
- ❌ **No pueden (responde `403`):** `inventario.test` — no tiene ningún permiso sobre `party-identity`; `reportes.test`, `consulta.test` — tienen permisos sobre `party-identity`, pero ninguno sobre `organization_contact_persons`

**Por qué se hace así**

- Por defecto solo los activos; `?is_active=false` muestra los inactivos.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "total_records": 1
}
```

---

[← Paso anterior](03-registrar-contactos.md) · [Orden del ejercicio](ORDEN.md)
