# Paso 02 de 04 — Registrar la organización y la persona

Ejercicio 6 — Personas de contacto: principal, set-primary e inactivación · [← Paso anterior](01-consultar-pais.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](03-registrar-contactos.md)

**Objetivo:** Crear las identidades globales.

**Necesita (de pasos anteriores):** `<PAIS_CO>` — pasos [01](01-consultar-pais.md)

**Deja guardado para los siguientes pasos:** `<ORG_LAB>`, `<PERSONA_MARTA>`

---

## 1. Registrar la organización

```http
POST /api/v1/organization-identities
```

```json
{
  "country_id": "<PAIS_CO>",
  "identification_type": "NIT",
  "identification_number": "900000006-6",
  "legal_name": "LABORATORIO CONTACTOS FICTICIO S.A.S."
}
```

**Permiso que exige la URL:** `perm:party-identity:organization_identities:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `party-identity` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `party-identity`

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<ORG_LAB>",
  "legal_name": "LABORATORIO CONTACTOS FICTICIO S.A.S.",
  "status": "ACTIVE"
}
```

**Guardar:** `id` → `<ORG_LAB>`

## 2. Registrar la persona de contacto

```http
POST /api/v1/person-identities
```

```json
{
  "identification_country_id": "<PAIS_CO>",
  "identification_type": "CC",
  "identification_number": "1000000006",
  "first_name": "MARTA",
  "last_name": "COMERCIAL",
  "second_last_name": "FICTICIA",
  "birth_date": "1988-07-01"
}
```

**Permiso que exige la URL:** `perm:party-identity:person_identities:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `party-identity` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `party-identity`

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<PERSONA_MARTA>",
  "first_name": "MARTA",
  "last_name": "COMERCIAL",
  "status": "ACTIVE"
}
```

**Guardar:** `id` → `<PERSONA_MARTA>`

---

[← Paso anterior](01-consultar-pais.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](03-registrar-contactos.md)
