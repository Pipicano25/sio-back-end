# Paso 05 de 05 — Cerrar el perfil sin reemplazo

Ejercicio 4 — Perfil de contacto de una organización: versiones, no-op y cierre · [← Paso anterior](04-reemplazar-y-rechazos.md) · [Orden del ejercicio](ORDEN.md)

**Objetivo:** Dejar la organización sin perfil vigente.

**Necesita (de pasos anteriores):** `<ORG_PROVEEDOR>` — pasos [02](02-registrar-organizacion.md)

---

## 1. Cerrar el perfil vigente

```http
POST /api/v1/organization-identities/<ORG_PROVEEDOR>/contact-profile:close
```

```json
{
  "version": 3
}
```

**Permiso que exige la URL:** `perm:party-identity:organization_contact_profiles:delete`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`)
- ❌ **No pueden (responde `403`):** `supervisor.test` — sobre `party-identity` solo tiene `create`, `read`, `update`; le falta `delete`; `compras.test`, `ventas.test` — sobre `party-identity` solo tienen `read`; les falta `delete`; `inventario.test` — no tiene ningún permiso sobre `party-identity`; `reportes.test`, `consulta.test` — tienen permisos sobre `party-identity`, pero ninguno sobre `organization_contact_profiles`
- ℹ️ Cerrar el perfil (`POST .../contact-profile:close`) exige `delete`, aunque no elimina: la versión queda en el historial.

**Por qué se hace así**

- Exige `delete` sobre `organization_contact_profiles`, aunque no borra: la versión queda en el historial.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "id": "<PERFIL_2>",
  "email": "compras@distribuidora-ficticia.co",
  "phone": "+57 601 555 0144",
  "city_id": "<CIUDAD>",
  "is_active": false,
  "confirmed_by_company_id": "<EMPRESA>",
  "confirmed_by_user_id": "<id generado>",
  "version": 4
}
```

## 2. Repetir el cierre (rechazado)

```http
POST /api/v1/organization-identities/<ORG_PROVEEDOR>/contact-profile:close
```

```json
{
  "version": 4
}
```

**Permiso que exige la URL:** `perm:party-identity:organization_contact_profiles:delete`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`)
- ❌ **No pueden (responde `403`):** `supervisor.test` — sobre `party-identity` solo tiene `create`, `read`, `update`; le falta `delete`; `compras.test`, `ventas.test` — sobre `party-identity` solo tienen `read`; les falta `delete`; `inventario.test` — no tiene ningún permiso sobre `party-identity`; `reportes.test`, `consulta.test` — tienen permisos sobre `party-identity`, pero ninguno sobre `organization_contact_profiles`
- ℹ️ Cerrar el perfil (`POST .../contact-profile:close`) exige `delete`, aunque no elimina: la versión queda en el historial.

**Por qué se hace así**

- Ya no hay vigente pero sí historia: `409 CONTACT_PROFILE_ALREADY_CLOSED` (si nunca hubiera tenido perfil sería `404 CONTACT_PROFILE_NOT_FOUND`).

**Respuesta esperada (error) — `409 Conflict`** (abreviada)

```json
{
  "status": 409,
  "code": "PARTY_IDENTITY.CONTACT_PROFILE_ALREADY_CLOSED"
}
```

## 3. Consultar el perfil vigente (ya no hay)

```http
GET /api/v1/organization-identities/<ORG_PROVEEDOR>/contact-profile
```

**Permiso que exige la URL:** `perm:party-identity:organization_contact_profiles:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:party-identity:organization_contact_profiles:read`), `ventas.test` (por `perm:party-identity:organization_contact_profiles:read`)
- ❌ **No pueden (responde `403`):** `inventario.test` — no tiene ningún permiso sobre `party-identity`; `reportes.test`, `consulta.test` — tienen permisos sobre `party-identity`, pero ninguno sobre `organization_contact_profiles`

**Por qué se hace así**

- `404 CONTACT_PROFILE_NOT_FOUND`: la organización existe, pero no tiene perfil vigente.

**Respuesta esperada (error) — `404`** (abreviada)

```json
{
  "status": 404,
  "code": "PARTY_IDENTITY.CONTACT_PROFILE_NOT_FOUND"
}
```

---

[← Paso anterior](04-reemplazar-y-rechazos.md) · [Orden del ejercicio](ORDEN.md)
