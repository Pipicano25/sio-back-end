# Paso 04 de 05 — Cambiar el asesor principal

Ejercicio 6 — Asesores de la empresa · [← Paso anterior](03-registrar-asesores.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](05-historial-y-cierre.md)

**Objetivo:** Reemplazar al asesor 1 por el asesor 2 en una sola operación.

**Necesita (de pasos anteriores):** `<EMPRESA>`, `<ASESORIA_1>`, `<PERSONA_ASESOR_2>` — pasos [01](01-consultar-datos.md), [02](02-registrar-empresa.md), [03](03-registrar-asesores.md)

**Deja guardado para los siguientes pasos:** `<ASESORIA_2>`

---

## 1. Cambiar el asesor principal

```http
POST /api/v1/companies/<EMPRESA>/advisor-assignments/change-primary
```

```json
{
  "current_assignment_id": "<ASESORIA_1>",
  "version": 1,
  "person_identity_id": "<PERSONA_ASESOR_2>",
  "effective_at": "2026-06-01T00:00:00-05:00"
}
```

**Permisos que exige la URL (todos):** `perm:operational-context:company_advisor_assignments:create` + `perm:operational-context:company_advisor_assignments:delete`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`)
- ❌ **No pueden (responde `403`):** `supervisor.test` — sobre `operational-context` solo tiene `create`, `read`, `update`; le falta `delete`; `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `operational-context` solo tienen `read`; les falta `create`
- 🔒 Aislamiento por empresa (Fase B): además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa o `platform:administer`; si no, la URL responde `404`, igual que un `id` inexistente.

**Por qué se hace así**

- Exige `create` **y** `delete` de asesores: `supervisor.test` no puede.
- Cierra la asignación 1 (`valid_to` = `effective_at`) y crea la 2 en la misma transacción.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "closed": {
    "id": "<ASESORIA_1>",
    "status": "INACTIVE"
  },
  "created": {
    "id": "<ASESORIA_2>",
    "person_identity_id": "<PERSONA_ASESOR_2>",
    "is_primary": true,
    "status": "ACTIVE"
  }
}
```

**Guardar:** `created.id` → `<ASESORIA_2>`

---

[← Paso anterior](03-registrar-asesores.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](05-historial-y-cierre.md)
