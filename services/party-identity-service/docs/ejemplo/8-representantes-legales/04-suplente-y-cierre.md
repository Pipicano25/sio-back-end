# Paso 04 de 04 — Suplente, historial y cierre

Ejercicio 8 — Representantes legales: PRIMARY único, set-primary y cierre · [← Paso anterior](03-establecer-primary.md) · [Orden del ejercicio](ORDEN.md)

**Objetivo:** Registrar un suplente y cerrarlo.

**Necesita (de pasos anteriores):** `<ORG_INV>`, `<PERSONA_JORGE>` — pasos [02](02-registrar-identidades.md)

**Deja guardado para los siguientes pasos:** `<REP_JORGE_SUPLENTE>`

---

## 1. Registrar a JORGE como suplente

```http
POST /api/v1/organization-identities/<ORG_INV>/legal-representatives
```

```json
{
  "person_identity_id": "<PERSONA_JORGE>",
  "representative_type": "ALTERNATE",
  "source_document_reference": "   "
}
```

**Permiso que exige la URL:** `perm:party-identity:organization_legal_representatives:create`

- ✅ **Pueden:** `admin.sio` (por `perm:all:all:all`), `admin.dao` (por `perm:party-identity:all:create`)
- ❌ **No pueden (responde `403`):** `operario.dao` — sobre `party-identity` solo tiene `read`; le falta `create`
- ℹ️ `:set-primary` también exige `create`: crea el primer `PRIMARY` o sustituye el vigente cerrándolo.

**Por qué se hace así**

- Su relación anterior está cerrada: se crea una fila nueva (las cerradas no se reactivan).
- Una referencia documental de solo espacios se guarda como `null`.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<REP_JORGE_SUPLENTE>",
  "person_identity_id": "<PERSONA_JORGE>",
  "representative_type": "ALTERNATE",
  "is_primary": false,
  "is_active": true,
  "source_document_reference": null,
  "version": 1
}
```

**Guardar:** `id` → `<REP_JORGE_SUPLENTE>`

## 2. Cerrar la relación de suplente

```http
POST /api/v1/organization-legal-representatives/<REP_JORGE_SUPLENTE>:close
```

**Permiso que exige la URL:** `perm:party-identity:organization_legal_representatives:delete`

- ✅ **Pueden:** `admin.sio` (por `perm:all:all:all`)
- ❌ **No pueden (responde `403`):** `admin.dao` — sobre `party-identity` solo tiene `create`, `read`, `update`; le falta `delete`; `operario.dao` — sobre `party-identity` solo tiene `read`; le falta `delete`

**Por qué se hace así**

- Exige `delete`; no borra.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "id": "<REP_JORGE_SUPLENTE>",
  "person_identity_id": "<PERSONA_JORGE>",
  "representative_type": "ALTERNATE",
  "is_primary": false,
  "is_active": false,
  "source_document_reference": null,
  "version": 2
}
```

## 3. Consultar el historial

```http
GET /api/v1/organization-identities/<ORG_INV>/legal-representatives?state=all
```

**Permiso que exige la URL:** `perm:party-identity:organization_legal_representatives:read`

- ✅ **Pueden:** `admin.sio` (por `perm:all:all:all`), `admin.dao` (por `perm:party-identity:all:read`), `operario.dao` (por `perm:party-identity:organization_legal_representatives:read`)
- ℹ️ Dato sensible: solo lo leen los grupos con necesidad explícita. Con los grupos de la spec 026 lo leen `superadmin`, `admin`, `Compras` y `Ventas`; solo `superadmin` y `admin` lo crean o modifican.

**Por qué se hace así**

- `state=active` (por defecto), `closed` o `all`.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "total_records": 3
}
```

---

[← Paso anterior](03-establecer-primary.md) · [Orden del ejercicio](ORDEN.md)
