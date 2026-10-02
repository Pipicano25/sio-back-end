# Paso 04 de 04 — Inactivar la persona

Ejercicio 2 — Personas: registrar, validar, verificar e inactivar · [← Paso anterior](03-verificar-persona.md) · [Orden del ejercicio](ORDEN.md)

**Objetivo:** Retirarla de uso sin borrarla y consultarla con filtro explícito.

**Necesita (de pasos anteriores):** `<PERSONA_ANA>` — pasos [02](02-registrar-persona.md)

---

## 1. Inactivar a ANA MARIA

```http
POST /api/v1/person-identities/<PERSONA_ANA>/deactivate
```

```json
{
  "version": 2
}
```

**Permiso que exige la URL:** `perm:party-identity:person_identities:delete`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`)
- ❌ **No pueden (responde `403`):** `supervisor.test` — sobre `party-identity` solo tiene `create`, `read`, `update`; le falta `delete`; `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `party-identity` solo tienen `read`; les falta `delete`; `inventario.test` — no tiene ningún permiso sobre `party-identity`
- ℹ️ Inactivar (`POST .../deactivate`) exige `delete`, aunque no elimina; reactivar (`POST .../reactivate`) exige `update`.

**Por qué se hace así**

- Inactivar exige `delete` sobre `person_identities`; reactivar (`/reactivate`) exige `update`.
- `verification_status` sigue `VERIFIED`: son estados independientes.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "id": "<PERSONA_ANA>",
  "verification_status": "VERIFIED",
  "status": "INACTIVE",
  "version": 3
}
```

## 2. Listar personas (por defecto solo `ACTIVE`)

```http
GET /api/v1/person-identities
```

**Permiso que exige la URL:** `perm:party-identity:person_identities:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:party-identity:person_identities:read`), `ventas.test` (por `perm:party-identity:person_identities:read`), `reportes.test` (por `perm:party-identity:person_identities:read`), `consulta.test` (por `perm:party-identity:person_identities:read`)
- ❌ **No pueden (responde `403`):** `inventario.test` — no tiene ningún permiso sobre `party-identity`

**Por qué se hace así**

- Sin filtro de estado la lista muestra solo personas activas: ANA MARIA ya no aparece.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "total_records": 0
}
```

## 3. Listar personas inactivas

```http
GET /api/v1/person-identities?status=INACTIVE
```

**Permiso que exige la URL:** `perm:party-identity:person_identities:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:party-identity:person_identities:read`), `ventas.test` (por `perm:party-identity:person_identities:read`), `reportes.test` (por `perm:party-identity:person_identities:read`), `consulta.test` (por `perm:party-identity:person_identities:read`)
- ❌ **No pueden (responde `403`):** `inventario.test` — no tiene ningún permiso sobre `party-identity`

**Por qué se hace así**

- Las inactivas se consultan con `status=INACTIVE`. Por `id` se devuelve en cualquier estado.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "id": "<PERSONA_ANA>",
      "status": "INACTIVE"
    }
  ],
  "total_records": 1
}
```

---

[← Paso anterior](03-verificar-persona.md) · [Orden del ejercicio](ORDEN.md)
