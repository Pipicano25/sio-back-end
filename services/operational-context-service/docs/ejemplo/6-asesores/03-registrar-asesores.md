# Paso 03 de 05 — Registrar los asesores

Ejercicio 6 — Asesores de la empresa · [← Paso anterior](02-registrar-empresa.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](04-cambiar-asesor-principal.md)

**Objetivo:** Registrar el asesor principal y uno no principal.

**Necesita (de pasos anteriores):** `<EMPRESA>`, `<PERSONA_ASESOR_1>`, `<PERSONA_ASESOR_2>`, `<PERSONA_ASESOR_3>` — pasos [01](01-consultar-datos.md), [02](02-registrar-empresa.md)

**Deja guardado para los siguientes pasos:** `<ASESORIA_1>`, `<ASESORIA_3>`

---

## 1. Registrar el asesor principal

```http
POST /api/v1/companies/<EMPRESA>/advisor-assignments
```

```json
{
  "person_identity_id": "<PERSONA_ASESOR_1>",
  "valid_from": "2026-01-01T00:00:00-05:00"
}
```

**Permiso que exige la URL:** `perm:operational-context:company_advisor_assignments:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `operational-context` solo tienen `read`; les falta `create`
- 🔒 Aislamiento por empresa (Fase B): además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa o `platform:administer`; si no, la URL responde `404`, igual que un `id` inexistente.

**Por qué se hace así**

- `is_primary` es `true` por defecto; `valid_from` puede ser pasada, nunca futura.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<ASESORIA_1>",
  "person_identity_id": "<PERSONA_ASESOR_1>",
  "is_primary": true,
  "status": "ACTIVE",
  "assigned_by": "user-admin",
  "version": 1
}
```

**Guardar:** `id` → `<ASESORIA_1>`

## 2. Intentar un segundo asesor principal (rechazado)

```http
POST /api/v1/companies/<EMPRESA>/advisor-assignments
```

```json
{
  "person_identity_id": "<PERSONA_ASESOR_2>"
}
```

**Permiso que exige la URL:** `perm:operational-context:company_advisor_assignments:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `operational-context` solo tienen `read`; les falta `create`
- 🔒 Aislamiento por empresa (Fase B): además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa o `platform:administer`; si no, la URL responde `404`, igual que un `id` inexistente.

**Por qué se hace así**

- Ya hay un principal vigente: `409 PRIMARY_ADVISOR_EXISTS`; para reemplazarlo se usa `change-primary`.

**Respuesta esperada (error) — `409 Conflict`** (abreviada)

```json
{
  "status": 409,
  "code": "OPERATIONAL_CONTEXT.PRIMARY_ADVISOR_EXISTS",
  "detail": "La empresa ya tiene un asesor principal vigente; use el cambio de asesor principal."
}
```

## 3. Registrar un asesor no principal

```http
POST /api/v1/companies/<EMPRESA>/advisor-assignments
```

```json
{
  "person_identity_id": "<PERSONA_ASESOR_3>",
  "is_primary": false,
  "valid_from": "2026-02-01T00:00:00-05:00"
}
```

**Permiso que exige la URL:** `perm:operational-context:company_advisor_assignments:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `operational-context` solo tienen `read`; les falta `create`
- 🔒 Aislamiento por empresa (Fase B): además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa o `platform:administer`; si no, la URL responde `404`, igual que un `id` inexistente.

**Por qué se hace así**

- Puede haber varios asesores vigentes; solo uno principal.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<ASESORIA_3>",
  "person_identity_id": "<PERSONA_ASESOR_3>",
  "is_primary": false,
  "status": "ACTIVE",
  "assigned_by": "user-admin",
  "version": 1
}
```

**Guardar:** `id` → `<ASESORIA_3>`

---

[← Paso anterior](02-registrar-empresa.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](04-cambiar-asesor-principal.md)
