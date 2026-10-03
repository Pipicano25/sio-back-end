# Paso 02 de 04 — Registrar la organización y las personas

Ejercicio 8 — Representantes legales: PRIMARY único, set-primary y cierre · [← Paso anterior](01-consultar-pais.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](03-establecer-primary.md)

**Objetivo:** Crear las identidades.

**Necesita (de pasos anteriores):** `<PAIS_CO>` — pasos [01](01-consultar-pais.md)

**Deja guardado para los siguientes pasos:** `<ORG_INV>`, `<PERSONA_JORGE>`, `<PERSONA_ELENA>`

---

## 1. Registrar la organización

```http
POST /api/v1/organization-identities
```

```json
{
  "country_id": "<PAIS_CO>",
  "identification_type": "NIT",
  "identification_number": "900000008-8",
  "legal_name": "INVERSIONES REPRESENTACION FICTICIA S.A.S."
}
```

**Permiso que exige la URL:** `perm:party-identity:organization_identities:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `party-identity` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `party-identity`

**Por qué se hace así**

- Las personas de contacto, sectores y representantes cuelgan de una organización `ACTIVE` de Party Identity; se registra primero con datos **ficticios** (NIT que cumple la regla `NIT`, no es real).

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<ORG_INV>",
  "legal_name": "INVERSIONES REPRESENTACION FICTICIA S.A.S.",
  "status": "ACTIVE"
}
```

**Guardar:** `id` → `<ORG_INV>`

## 2. Registrar la primera persona

```http
POST /api/v1/person-identities
```

```json
{
  "identification_country_id": "<PAIS_CO>",
  "identification_type": "CC",
  "identification_number": "1000000081",
  "first_name": "JORGE",
  "last_name": "REPRESENTANTE",
  "second_last_name": "FICTICIO",
  "birth_date": "1975-01-15"
}
```

**Permiso que exige la URL:** `perm:party-identity:person_identities:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `party-identity` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `party-identity`

**Por qué se hace así**

- Un representante es una `PersonIdentity` `ACTIVE` de Party Identity (datos **ficticios**); la relación guarda solo su `id`.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<PERSONA_JORGE>",
  "first_name": "JORGE",
  "status": "ACTIVE"
}
```

**Guardar:** `id` → `<PERSONA_JORGE>`

## 3. Registrar la segunda persona

```http
POST /api/v1/person-identities
```

```json
{
  "identification_country_id": "<PAIS_CO>",
  "identification_type": "CC",
  "identification_number": "1000000082",
  "first_name": "ELENA",
  "last_name": "REPRESENTANTE",
  "second_last_name": "FICTICIO",
  "birth_date": "1975-01-15"
}
```

**Permiso que exige la URL:** `perm:party-identity:person_identities:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `party-identity` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `party-identity`

**Por qué se hace así**

- Un representante es una `PersonIdentity` `ACTIVE` de Party Identity (datos **ficticios**); la relación guarda solo su `id`.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<PERSONA_ELENA>",
  "first_name": "ELENA",
  "status": "ACTIVE"
}
```

**Guardar:** `id` → `<PERSONA_ELENA>`

---

[← Paso anterior](01-consultar-pais.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](03-establecer-primary.md)
