# Paso 02 de 05 — Registrar la empresa, sus sucursales y el usuario

Ejercicio 5 — Sucursales asignadas y acceso operativo · [← Paso anterior](01-consultar-datos.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](03-asignar-sucursal.md)

**Objetivo:** Crear la empresa, dos sucursales y la membresía de `operario.dao`.

**Necesita (de pasos anteriores):** `<ORG_EMPRESA>`, `<PERSONA_COMPRADOR>` — pasos [01](01-consultar-datos.md)

**Deja guardado para los siguientes pasos:** `<EMPRESA>`, `<SUC_PRINCIPAL>`, `<SUC_SECUNDARIA>`, `<USR_COMPRADOR>`

---

## 1. Registrar la empresa

```http
POST /api/v1/companies
```

```json
{
  "organization_identity_id": "<ORG_EMPRESA>"
}
```

**Permisos que exige la URL (todos):** `perm:operational-context:companies:create` + `perm:operational-context:platform:administer`

- ✅ **Pueden:** `admin.sio` (por `perm:all:all:all`)
- ❌ **No pueden (responde `403`):** `admin.dao` — sobre `operational-context` solo tiene `create`, `delete`, `read`, `update`; le falta `administer`; `operario.dao` — sobre `operational-context` solo tiene `read`; le falta `create`
- ℹ️ Para registrar o cambiar la organización o la ubicación, el token del usuario debe poder además **leer** en Party Identity y Geography: el servicio valida esas referencias con el mismo token. La tienen `superadmin`, `admin`, `Compras` y `Ventas` (`Inventario` no lee Party Identity).
- ℹ️ Alcance de plataforma (Fase B, DS-05): registrar, inactivar y reactivar empresas y ver todas las empresas sin ser miembro. Solo lo concede `perm:all:all:all` (grupo `superadmin`); los comodines de lectura, creación, modificación o eliminación **no** lo conceden.

**Por qué se hace así**

- Solo el administrador de plataforma registra empresas.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<EMPRESA>",
  "status": "ACTIVE"
}
```

**Guardar:** `id` → `<EMPRESA>`

## 2. Registrar la sucursal principal

```http
POST /api/v1/companies/<EMPRESA>/branches
```

```json
{
  "code": "PRI-01",
  "name": "Principal (ficticia)"
}
```

**Permiso que exige la URL:** `perm:operational-context:branches:create`

- ✅ **Pueden:** `admin.sio` (por `perm:all:all:all`), `admin.dao` (por `perm:operational-context:all:create`)
- ❌ **No pueden (responde `403`):** `operario.dao` — sobre `operational-context` solo tiene `read`; le falta `create`
- 🔒 Aislamiento por empresa (Fase B): además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa o `platform:administer`; si no, la URL responde `404`, igual que un `id` inexistente.

**Por qué se hace así**

- Sucursal a la que se asignará el usuario.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<SUC_PRINCIPAL>",
  "code": "PRI-01",
  "status": "ACTIVE"
}
```

**Guardar:** `id` → `<SUC_PRINCIPAL>`

## 3. Registrar la sucursal secundaria

```http
POST /api/v1/companies/<EMPRESA>/branches
```

```json
{
  "code": "SEC-01",
  "name": "Secundaria (ficticia)"
}
```

**Permiso que exige la URL:** `perm:operational-context:branches:create`

- ✅ **Pueden:** `admin.sio` (por `perm:all:all:all`), `admin.dao` (por `perm:operational-context:all:create`)
- ❌ **No pueden (responde `403`):** `operario.dao` — sobre `operational-context` solo tiene `read`; le falta `create`
- 🔒 Aislamiento por empresa (Fase B): además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa o `platform:administer`; si no, la URL responde `404`, igual que un `id` inexistente.

**Por qué se hace así**

- Sucursal sin asignar, para ver `BRANCH_NOT_ASSIGNED`.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<SUC_SECUNDARIA>",
  "code": "SEC-01",
  "status": "ACTIVE"
}
```

**Guardar:** `id` → `<SUC_SECUNDARIA>`

## 4. Registrar a operario.dao como usuario operativo

```http
POST /api/v1/companies/<EMPRESA>/application-users
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

- La membresía es requisito del acceso operativo.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<USR_COMPRADOR>",
  "keycloak_user_id": "operario.dao",
  "status": "ACTIVE"
}
```

**Guardar:** `id` → `<USR_COMPRADOR>`

---

[← Paso anterior](01-consultar-datos.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](03-asignar-sucursal.md)
