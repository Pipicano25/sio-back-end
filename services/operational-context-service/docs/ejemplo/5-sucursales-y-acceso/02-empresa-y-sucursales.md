# Paso 02 de 05 — Registrar la empresa, sus sucursales y el usuario

Ejercicio 5 — Sucursales asignadas y acceso operativo · [← Paso anterior](01-consultar-datos.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](03-asignar-sucursal.md)

**Objetivo:** Crear la empresa, dos sucursales y la membresía de `compras.test`.

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

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`)
- ❌ **No pueden (responde `403`):** `supervisor.test` — sobre `operational-context` solo tiene `create`, `read`, `update`; le falta `administer`; `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `operational-context` solo tienen `read`; les falta `create`
- ℹ️ Para registrar o cambiar la organización o la ubicación, el token del usuario debe poder además **leer** en Party Identity y Geography: el servicio valida esas referencias con el mismo token. `administradores` y `supervisores` tienen esa lectura.
- ℹ️ Alcance de plataforma (Fase B, DS-05): registrar, inactivar y reactivar empresas y ver todas las empresas sin ser miembro. Solo lo concede `perm:all:all:all` (`administradores`); los comodines de lectura, creación o modificación **no** lo conceden.

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

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `operational-context` solo tienen `read`; les falta `create`
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

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `operational-context` solo tienen `read`; les falta `create`
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

## 4. Registrar a compras.test como usuario operativo

```http
POST /api/v1/companies/<EMPRESA>/application-users
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

- La membresía es requisito del acceso operativo.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<USR_COMPRADOR>",
  "keycloak_user_id": "compras.test",
  "status": "ACTIVE"
}
```

**Guardar:** `id` → `<USR_COMPRADOR>`

---

[← Paso anterior](01-consultar-datos.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](03-asignar-sucursal.md)
