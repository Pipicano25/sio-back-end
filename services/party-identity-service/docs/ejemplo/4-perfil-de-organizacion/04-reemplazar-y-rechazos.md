# Paso 04 de 05 — Reemplazar el perfil y rechazos

Ejercicio 4 — Perfil de contacto de una organización: versiones, no-op y cierre · [← Paso anterior](03-registrar-perfil.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](05-cerrar-perfil.md)

**Objetivo:** Crear una versión nueva y ver los rechazos.

**Necesita (de pasos anteriores):** `<ORG_PROVEEDOR>`, `<PAIS_CO>`, `<DIVISION>`, `<CIUDAD>`, `<EMPRESA>` — pasos [01](01-consultar-referencias.md), [02](02-registrar-organizacion.md)

**Deja guardado para los siguientes pasos:** `<PERFIL_2>`

---

## 1. Reemplazar el teléfono (nueva versión)

```http
POST /api/v1/organization-identities/<ORG_PROVEEDOR>/contact-profile
```

```json
{
  "email": "compras@distribuidora-ficticia.co",
  "phone": "+57 601 555 0144",
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

- Se envía el conjunto completo y la `version` de la vigente. La versión 1 queda cerrada con `valid_to` y se crea otra vigente.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<PERFIL_2>",
  "email": "compras@distribuidora-ficticia.co",
  "phone": "+57 601 555 0144",
  "city_id": "<CIUDAD>",
  "is_active": true,
  "confirmed_by_company_id": "<EMPRESA>",
  "confirmed_by_user_id": "<id generado>",
  "version": 3
}
```

**Guardar:** `id` → `<PERFIL_2>`

## 2. Intentar una división administrativa inexistente (rechazado)

```http
POST /api/v1/organization-identities/<ORG_PROVEEDOR>/contact-profile
```

```json
{
  "email": "compras@distribuidora-ficticia.co",
  "phone": "+57 601 555 0104",
  "address_line": "Calle 00 # 00-04 (ficticia)",
  "country_id": "<PAIS_CO>",
  "administrative_division_id": "5e0c0f6e-0000-4000-8000-00000000dead",
  "city_id": "<CIUDAD>",
  "postal_code": "110111",
  "confirmed_by_company_id": "<EMPRESA>",
  "version": 3
}
```

**Permiso que exige la URL:** `perm:party-identity:organization_contact_profiles:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test` — sobre `party-identity` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `party-identity`; `reportes.test`, `consulta.test` — tienen permisos sobre `party-identity`, pero ninguno sobre `organization_contact_profiles`
- ℹ️ Registrar una versión del perfil exige además que el usuario tenga una membresía `ACTIVE` en la empresa indicada (la comprueba Party Identity con su cliente técnico contra Operational Context). El usuario **no** necesita permisos de Operational Context; un administrador de plataforma sin membresía recibe `422 CONFIRMATION_MEMBERSHIP_INVALID`.

**Por qué se hace así**

- La división enviada no existe en Geography: `422 ADMINISTRATIVE_DIVISION_NOT_FOUND`; no se guarda nada.

**Respuesta esperada (error) — `422 Unprocessable Content`** (abreviada)

```json
{
  "status": 422,
  "code": "PARTY_IDENTITY.ADMINISTRATIVE_DIVISION_NOT_FOUND",
  "detail": "La división administrativa indicada no existe en Geography Service."
}
```

## 3. Intentar confirmar desde una empresa sin membresía (rechazado)

```http
POST /api/v1/organization-identities/<ORG_PROVEEDOR>/contact-profile
```

```json
{
  "email": "compras@distribuidora-ficticia.co",
  "phone": "+57 601 555 0145",
  "address_line": "Calle 00 # 00-04 (ficticia)",
  "country_id": "<PAIS_CO>",
  "administrative_division_id": "<DIVISION>",
  "city_id": "<CIUDAD>",
  "postal_code": "110111",
  "confirmed_by_company_id": "6a1d0000-0000-4000-8000-000000000002",
  "version": 3
}
```

**Permiso que exige la URL:** `perm:party-identity:organization_contact_profiles:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test` — sobre `party-identity` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `party-identity`; `reportes.test`, `consulta.test` — tienen permisos sobre `party-identity`, pero ninguno sobre `organization_contact_profiles`
- ℹ️ Registrar una versión del perfil exige además que el usuario tenga una membresía `ACTIVE` en la empresa indicada (la comprueba Party Identity con su cliente técnico contra Operational Context). El usuario **no** necesita permisos de Operational Context; un administrador de plataforma sin membresía recibe `422 CONFIRMATION_MEMBERSHIP_INVALID`.

**Por qué se hace así**

- El usuario no es miembro de esa empresa: `422 CONFIRMATION_MEMBERSHIP_INVALID` con `reason: USER_NOT_MEMBER`. Ser administrador no basta.

**Respuesta esperada (error) — `422 Unprocessable Content`** (abreviada)

```json
{
  "status": 422,
  "code": "PARTY_IDENTITY.CONFIRMATION_MEMBERSHIP_INVALID",
  "reason": "USER_NOT_MEMBER"
}
```

## 4. Intentar con Operational Context no disponible (simulado, rechazado)

```http
POST /api/v1/organization-identities/<ORG_PROVEEDOR>/contact-profile
```

```json
{
  "email": "compras@distribuidora-ficticia.co",
  "phone": "+57 601 555 0146",
  "address_line": "Calle 00 # 00-04 (ficticia)",
  "country_id": "<PAIS_CO>",
  "administrative_division_id": "<DIVISION>",
  "city_id": "<CIUDAD>",
  "postal_code": "110111",
  "confirmed_by_company_id": "6a1d0000-0000-4000-8000-000000000003",
  "version": 3
}
```

**Permiso que exige la URL:** `perm:party-identity:organization_contact_profiles:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test` — sobre `party-identity` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `party-identity`; `reportes.test`, `consulta.test` — tienen permisos sobre `party-identity`, pero ninguno sobre `organization_contact_profiles`
- ℹ️ Registrar una versión del perfil exige además que el usuario tenga una membresía `ACTIVE` en la empresa indicada (la comprueba Party Identity con su cliente técnico contra Operational Context). El usuario **no** necesita permisos de Operational Context; un administrador de plataforma sin membresía recibe `422 CONFIRMATION_MEMBERSHIP_INVALID`.

**Por qué se hace así**

- Responde `503 DEPENDENCY_UNAVAILABLE` con `dependency: operational-context`; no se guarda nada.

**Respuesta esperada (error) — `503`** (abreviada)

```json
{
  "status": 503,
  "code": "PARTY_IDENTITY.DEPENDENCY_UNAVAILABLE",
  "dependency": "operational-context"
}
```

## 5. Consultar el historial de versiones

```http
GET /api/v1/organization-identities/<ORG_PROVEEDOR>/contact-profile/versions
```

**Permiso que exige la URL:** `perm:party-identity:organization_contact_profiles:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:party-identity:organization_contact_profiles:read`), `ventas.test` (por `perm:party-identity:organization_contact_profiles:read`)
- ❌ **No pueden (responde `403`):** `inventario.test` — no tiene ningún permiso sobre `party-identity`; `reportes.test`, `consulta.test` — tienen permisos sobre `party-identity`, pero ninguno sobre `organization_contact_profiles`

**Por qué se hace así**

- Las versiones se conservan, de la más reciente a la más antigua, con quién y desde qué empresa se confirmó cada una.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "total_records": 2
}
```

---

[← Paso anterior](03-registrar-perfil.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](05-cerrar-perfil.md)
