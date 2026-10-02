# Paso 03 de 05 — Registrar el perfil y repetirlo

Ejercicio 4 — Perfil de contacto de una organización: versiones, no-op y cierre · [← Paso anterior](02-registrar-organizacion.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](04-reemplazar-y-rechazos.md)

**Objetivo:** Crear la versión vigente; la repetición no cambia nada.

**Necesita (de pasos anteriores):** `<ORG_PROVEEDOR>`, `<PAIS_CO>`, `<DIVISION>`, `<CIUDAD>`, `<EMPRESA>` — pasos [01](01-consultar-referencias.md), [02](02-registrar-organizacion.md)

**Deja guardado para los siguientes pasos:** `<PERFIL_1>`

---

## 1. Registrar el perfil de contacto (confirmado desde la empresa)

```http
POST /api/v1/organization-identities/<ORG_PROVEEDOR>/contact-profile
```

```json
{
  "email": "compras@distribuidora-ficticia.co",
  "phone": "+57 601 555 0104",
  "address_line": "Calle 00 # 00-04 (ficticia)",
  "country_id": "<PAIS_CO>",
  "administrative_division_id": "<DIVISION>",
  "city_id": "<CIUDAD>",
  "postal_code": "110111",
  "confirmed_by_company_id": "<EMPRESA>"
}
```

**Permiso que exige la URL:** `perm:party-identity:organization_contact_profiles:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test` — sobre `party-identity` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `party-identity`; `reportes.test`, `consulta.test` — tienen permisos sobre `party-identity`, pero ninguno sobre `organization_contact_profiles`
- ℹ️ Registrar una versión del perfil exige además que el usuario tenga una membresía `ACTIVE` en la empresa indicada (la comprueba Party Identity con su cliente técnico contra Operational Context). El usuario **no** necesita permisos de Operational Context; un administrador de plataforma sin membresía recibe `422 CONFIRMATION_MEMBERSHIP_INVALID`.

**Por qué se hace así**

- Al menos uno de correo, teléfono o dirección es obligatorio.
- La geografía se valida contra Geography; la empresa y la membresía, contra Operational Context.
- La respuesta trae `confirmed_by_user_id`: el usuario operativo resuelto, nunca enviado.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<PERFIL_1>",
  "email": "compras@distribuidora-ficticia.co",
  "phone": "+57 601 555 0104",
  "city_id": "<CIUDAD>",
  "is_active": true,
  "confirmed_by_company_id": "<EMPRESA>",
  "confirmed_by_user_id": "<id generado>",
  "version": 1
}
```

**Guardar:** `id` → `<PERFIL_1>`

## 2. Repetir exactamente la misma solicitud (sin cambios)

```http
POST /api/v1/organization-identities/<ORG_PROVEEDOR>/contact-profile
```

```json
{
  "email": "compras@distribuidora-ficticia.co",
  "phone": "+57 601 555 0104",
  "address_line": "Calle 00 # 00-04 (ficticia)",
  "country_id": "<PAIS_CO>",
  "administrative_division_id": "<DIVISION>",
  "city_id": "<CIUDAD>",
  "postal_code": "110111",
  "confirmed_by_company_id": "<EMPRESA>",
  "version": 1
}
```

**Permiso que exige la URL:** `perm:party-identity:organization_contact_profiles:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test` — sobre `party-identity` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `party-identity`; `reportes.test`, `consulta.test` — tienen permisos sobre `party-identity`, pero ninguno sobre `organization_contact_profiles`
- ℹ️ Registrar una versión del perfil exige además que el usuario tenga una membresía `ACTIVE` en la empresa indicada (la comprueba Party Identity con su cliente técnico contra Operational Context). El usuario **no** necesita permisos de Operational Context; un administrador de plataforma sin membresía recibe `422 CONFIRMATION_MEMBERSHIP_INVALID`.

**Por qué se hace así**

- Es semánticamente idéntica a la vigente: responde `200` con la misma versión, sin crear otra, sin tocar `updated_at` ni consultar otros servicios.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "id": "<PERFIL_1>",
  "email": "compras@distribuidora-ficticia.co",
  "phone": "+57 601 555 0104",
  "city_id": "<CIUDAD>",
  "is_active": true,
  "confirmed_by_company_id": "<EMPRESA>",
  "confirmed_by_user_id": "<id generado>",
  "version": 1
}
```

## 3. Consultar el perfil vigente

```http
GET /api/v1/organization-identities/<ORG_PROVEEDOR>/contact-profile
```

**Permiso que exige la URL:** `perm:party-identity:organization_contact_profiles:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:party-identity:organization_contact_profiles:read`), `ventas.test` (por `perm:party-identity:organization_contact_profiles:read`)
- ❌ **No pueden (responde `403`):** `inventario.test` — no tiene ningún permiso sobre `party-identity`; `reportes.test`, `consulta.test` — tienen permisos sobre `party-identity`, pero ninguno sobre `organization_contact_profiles`

**Por qué se hace así**

- Es el contrato que usan Commercial Relationship, Purchase y Sales para mostrar el contacto.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "id": "<PERFIL_1>",
  "email": "compras@distribuidora-ficticia.co",
  "phone": "+57 601 555 0104",
  "city_id": "<CIUDAD>",
  "is_active": true,
  "confirmed_by_company_id": "<EMPRESA>",
  "confirmed_by_user_id": "<id generado>",
  "version": 1
}
```

---

[← Paso anterior](02-registrar-organizacion.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](04-reemplazar-y-rechazos.md)
