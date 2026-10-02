# Paso 03 de 04 — Establecer y sustituir el PRIMARY

Ejercicio 8 — Representantes legales: PRIMARY único, set-primary y cierre · [← Paso anterior](02-registrar-identidades.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](04-suplente-y-cierre.md)

**Objetivo:** Usar set-primary y ver el conflicto.

**Necesita (de pasos anteriores):** `<ORG_INV>`, `<PERSONA_JORGE>`, `<PERSONA_ELENA>` — pasos [02](02-registrar-identidades.md)

**Deja guardado para los siguientes pasos:** `<REP_JORGE>`, `<REP_ELENA>`

---

## 1. Establecer el primer PRIMARY

```http
POST /api/v1/organization-identities/<ORG_INV>/legal-representatives:set-primary
```

```json
{
  "person_identity_id": "<PERSONA_JORGE>",
  "position": "Gerente general"
}
```

**Permiso que exige la URL:** `perm:party-identity:organization_legal_representatives:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — tienen permisos sobre `party-identity`, pero ninguno sobre `organization_legal_representatives`; `inventario.test` — no tiene ningún permiso sobre `party-identity`
- ℹ️ `:set-primary` también exige `create`: crea el primer `PRIMARY` o sustituye el vigente cerrándolo.

**Por qué se hace así**

- No hay `PRIMARY` vigente: se crea el primero (no se envía `current_primary_version`).

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<REP_JORGE>",
  "person_identity_id": "<PERSONA_JORGE>",
  "representative_type": "PRIMARY",
  "is_primary": true,
  "is_active": true,
  "source_document_reference": null,
  "version": 1
}
```

**Guardar:** `id` → `<REP_JORGE>`

## 2. Intentar registrar otro PRIMARY por el alta ordinaria (rechazado)

```http
POST /api/v1/organization-identities/<ORG_INV>/legal-representatives
```

```json
{
  "person_identity_id": "<PERSONA_ELENA>",
  "representative_type": "PRIMARY"
}
```

**Permiso que exige la URL:** `perm:party-identity:organization_legal_representatives:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — tienen permisos sobre `party-identity`, pero ninguno sobre `organization_legal_representatives`; `inventario.test` — no tiene ningún permiso sobre `party-identity`
- ℹ️ `:set-primary` también exige `create`: crea el primer `PRIMARY` o sustituye el vigente cerrándolo.

**Por qué se hace así**

- Ya hay uno: `409 PRIMARY_REPRESENTATIVE_CONFLICT`.

**Respuesta esperada (error) — `409 Conflict`** (abreviada)

```json
{
  "status": 409,
  "code": "PARTY_IDENTITY.PRIMARY_REPRESENTATIVE_CONFLICT"
}
```

## 3. Sustituir el PRIMARY

```http
POST /api/v1/organization-identities/<ORG_INV>/legal-representatives:set-primary
```

```json
{
  "person_identity_id": "<PERSONA_ELENA>",
  "position": "Gerente general",
  "current_primary_version": 1,
  "source_document_reference": "Acta 001 de 2026 (ficticia)"
}
```

**Permiso que exige la URL:** `perm:party-identity:organization_legal_representatives:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — tienen permisos sobre `party-identity`, pero ninguno sobre `organization_legal_representatives`; `inventario.test` — no tiene ningún permiso sobre `party-identity`
- ℹ️ `:set-primary` también exige `create`: crea el primer `PRIMARY` o sustituye el vigente cerrándolo.

**Por qué se hace así**

- Cierra la relación de JORGE (`valid_to`) y crea la de ELENA en la misma operación.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<REP_ELENA>",
  "person_identity_id": "<PERSONA_ELENA>",
  "representative_type": "PRIMARY",
  "is_primary": true,
  "is_active": true,
  "source_document_reference": "Acta 001 de 2026 (ficticia)",
  "version": 1
}
```

**Guardar:** `id` → `<REP_ELENA>`

---

[← Paso anterior](02-registrar-identidades.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](04-suplente-y-cierre.md)
