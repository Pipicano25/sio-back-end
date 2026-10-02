# Paso 02 de 03 — Registrar la persona y su perfil

Ejercicio 5 — Perfil de contacto de una persona: cliente persona natural e inactivación · [← Paso anterior](01-consultar-referencias.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](03-inactivar-persona.md)

**Objetivo:** Crear la persona y su contacto vigente.

**Necesita (de pasos anteriores):** `<PAIS_CO>`, `<EMPRESA>` — pasos [01](01-consultar-referencias.md)

**Deja guardado para los siguientes pasos:** `<PERSONA_CLIENTE>`

---

## 1. Registrar la persona

```http
POST /api/v1/person-identities
```

```json
{
  "identification_country_id": "<PAIS_CO>",
  "identification_type": "CC",
  "identification_number": "1000000005",
  "first_name": "LUIS",
  "last_name": "CLIENTE",
  "second_last_name": "FICTICIO",
  "birth_date": "1985-03-20"
}
```

**Permiso que exige la URL:** `perm:party-identity:person_identities:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `party-identity` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `party-identity`

**Por qué se hace así**

- Cédula moderna de 10 dígitos y persona adulta: cumple las reglas de Colombia.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<PERSONA_CLIENTE>",
  "first_name": "LUIS",
  "last_name": "CLIENTE",
  "status": "ACTIVE",
  "version": 1
}
```

**Guardar:** `id` → `<PERSONA_CLIENTE>`

## 2. Registrar el perfil de contacto

```http
POST /api/v1/person-identities/<PERSONA_CLIENTE>/contact-profile
```

```json
{
  "email": "luis.cliente@correo-ficticio.co",
  "phone": "+57 300 555 0105",
  "confirmed_by_company_id": "<EMPRESA>"
}
```

**Permiso que exige la URL:** `perm:party-identity:person_contact_profiles:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test` — sobre `party-identity` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `party-identity`; `reportes.test`, `consulta.test` — tienen permisos sobre `party-identity`, pero ninguno sobre `person_contact_profiles`
- ℹ️ Igual que en organizaciones: se exige membresía `ACTIVE` en la empresa desde la que se confirma, sin permisos de Operational Context.

**Por qué se hace así**

- Solo correo y teléfono; la empresa confirmante es obligatoria.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<id generado>",
  "email": "luis.cliente@correo-ficticio.co",
  "phone": "+57 300 555 0105",
  "is_active": true,
  "confirmed_by_company_id": "<EMPRESA>",
  "confirmed_by_user_id": "<id generado>",
  "version": 1
}
```

## 3. Consultar el perfil vigente

```http
GET /api/v1/person-identities/<PERSONA_CLIENTE>/contact-profile
```

**Permiso que exige la URL:** `perm:party-identity:person_contact_profiles:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:party-identity:person_contact_profiles:read`), `ventas.test` (por `perm:party-identity:person_contact_profiles:read`)
- ❌ **No pueden (responde `403`):** `inventario.test` — no tiene ningún permiso sobre `party-identity`; `reportes.test`, `consulta.test` — tienen permisos sobre `party-identity`, pero ninguno sobre `person_contact_profiles`

**Por qué se hace así**

- Lo usará Sales para contactar al cliente persona.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "id": "<id generado>",
  "email": "luis.cliente@correo-ficticio.co",
  "phone": "+57 300 555 0105",
  "is_active": true,
  "confirmed_by_company_id": "<EMPRESA>",
  "confirmed_by_user_id": "<id generado>",
  "version": 1
}
```

---

[← Paso anterior](01-consultar-referencias.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](03-inactivar-persona.md)
