# Paso 05 de 05 — Consultar el historial y cerrar un asesor

Ejercicio 6 — Asesores de la empresa · [← Paso anterior](04-cambiar-asesor-principal.md) · [Orden del ejercicio](ORDEN.md)

**Objetivo:** Ver el historial completo y cerrar al asesor no principal.

**Necesita (de pasos anteriores):** `<EMPRESA>`, `<ASESORIA_3>` — pasos [02](02-registrar-empresa.md), [03](03-registrar-asesores.md)

---

## 1. Consultar el historial de asesores

```http
GET /api/v1/companies/<EMPRESA>/advisor-assignments
```

**Permiso que exige la URL:** `perm:operational-context:company_advisor_assignments:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:operational-context:all:read`), `ventas.test` (por `perm:operational-context:all:read`), `inventario.test` (por `perm:operational-context:all:read`), `reportes.test` (por `perm:all:all:read`), `consulta.test` (por `perm:all:all:read`)
- 🔒 Aislamiento por empresa (Fase B): además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa o `platform:administer`; si no, la URL responde `404`, igual que un `id` inexistente.

**Por qué se hace así**

- Sin filtro de estado devuelve vigentes y cerradas, de la vigencia más reciente a la más antigua.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "person_identity_id": "<PERSONA_ASESOR_2>",
      "is_primary": true,
      "status": "ACTIVE"
    },
    {
      "person_identity_id": "<PERSONA_ASESOR_3>",
      "is_primary": false,
      "status": "ACTIVE"
    },
    {
      "person_identity_id": "<PERSONA_ASESOR_1>",
      "is_primary": true,
      "status": "INACTIVE"
    }
  ],
  "total_records": 3
}
```

## 2. Cerrar la asignación del asesor no principal

```http
POST /api/v1/advisor-assignments/<ASESORIA_3>/close
```

```json
{
  "version": 1,
  "valid_to": "2026-07-01T00:00:00-05:00"
}
```

**Permiso que exige la URL:** `perm:operational-context:company_advisor_assignments:delete`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`)
- ❌ **No pueden (responde `403`):** `supervisor.test` — sobre `operational-context` solo tiene `create`, `read`, `update`; le falta `delete`; `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `operational-context` solo tienen `read`; les falta `delete`
- 🔒 Aislamiento por empresa (Fase B): además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa o `platform:administer`; si no, la URL responde `404`, igual que un `id` inexistente.

**Por qué se hace así**

- Exige `delete`; no elimina: fija `valid_to` y la deja `INACTIVE`.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "id": "<ASESORIA_3>",
  "status": "INACTIVE",
  "version": 2
}
```

## 3. Intentar cerrarla otra vez (rechazado)

```http
POST /api/v1/advisor-assignments/<ASESORIA_3>/close
```

```json
{
  "version": 2
}
```

**Permiso que exige la URL:** `perm:operational-context:company_advisor_assignments:delete`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`)
- ❌ **No pueden (responde `403`):** `supervisor.test` — sobre `operational-context` solo tiene `create`, `read`, `update`; le falta `delete`; `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `operational-context` solo tienen `read`; les falta `delete`
- 🔒 Aislamiento por empresa (Fase B): además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa o `platform:administer`; si no, la URL responde `404`, igual que un `id` inexistente.

**Por qué se hace así**

- Una asignación cerrada es inmutable: `409 INVALID_STATUS_TRANSITION`.

**Respuesta esperada (error) — `409 Conflict`** (abreviada)

```json
{
  "status": 409,
  "code": "OPERATIONAL_CONTEXT.INVALID_STATUS_TRANSITION",
  "detail": "La asignación de asesor ya está cerrada."
}
```

---

[← Paso anterior](04-cambiar-asesor-principal.md) · [Orden del ejercicio](ORDEN.md)
