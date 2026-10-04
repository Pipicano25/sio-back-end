# Paso 01 de 04 — Consultar la empresa y las identidades

Ejercicio 2 — Clientes persona y organización · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](02-cliente-persona.md)

**Objetivo:** Obtener `<EMPRESA>`, la persona, las organizaciones y los contactos.

**Necesita (de pasos anteriores):** `<NIT>`

**Deja guardado para los siguientes pasos:** `<EMPRESA>`, `<ORG_EMPRESA>`, `<PERSONA>`, `<ORG_CLIENTE>`, `<CONTACTO>`, `<ORG_OTRA>`, `<CONTACTO_OTRA>`

---

## 1. Consultar la empresa COMERCIALIZADORA CLIENTES FICTICIA S.A.S. en Operational Context

> **Otro servicio:** esta llamada va a **Operational Context Service**, no a Commercial Relationship. No se ejecuta en la validación automática: su resultado se simula.

```http
GET http://localhost:8004/api/v1/me/operational-context
```

**Permiso que exige la URL:** `perm:operational-context:application_users:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:operational-context:all:read`), `ventas.test` (por `perm:operational-context:all:read`), `inventario.test` (por `perm:operational-context:all:read`), `reportes.test` (por `perm:operational-context:application_users:read`), `consulta.test` (por `perm:operational-context:application_users:read`)

**Por qué se hace así**

- Commercial Relationship **no guarda** empresas: usa el `company_id` de Operational Context y, en cada solicitud, le pregunta si el usuario tiene membresía `ACTIVE` en ella (DS-02).
- `me/operational-context` lista las empresas donde el usuario es miembro: de ahí se toma el `id`.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "keycloak_user_id": "<sub del usuario>",
  "memberships": [
    {
      "application_user_id": "<id generado>",
      "company_id": "<EMPRESA>",
      "company_status": "ACTIVE",
      "status": "ACTIVE",
      "branches": []
    }
  ]
}
```

**Guardar:** `memberships[0].company_id` → `<EMPRESA>`

## 2. Consultar la organización COMERCIALIZADORA CLIENTES FICTICIA S.A.S. en Party Identity

> **Otro servicio:** esta llamada va a **Party Identity Service**, no a Commercial Relationship. No se ejecuta en la validación automática: su resultado se simula.

```http
GET http://localhost:8002/api/v1/organization-identities?search=<NIT>
```

**Permiso que exige la URL:** `perm:party-identity:organization_identities:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:party-identity:organization_identities:read`), `ventas.test` (por `perm:party-identity:organization_identities:read`), `reportes.test` (por `perm:party-identity:organization_identities:read`), `consulta.test` (por `perm:party-identity:organization_identities:read`)
- ❌ **No pueden (responde `403`):** `inventario.test` — no tiene ningún permiso sobre `organization_identities` de `party-identity`

**Por qué se hace así**

- Commercial Relationship **no guarda** la razón social ni el NIT: solo el `id` de la `OrganizationIdentity` (Principio III). El NIT real se toma de una fuente oficial (RUT, RUES).

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "id": "<ORG_EMPRESA>",
      "identification_type": "NIT",
      "identification_number": "<NIT obtenido del RUT; dato ficticio aquí>",
      "legal_name": "COMERCIALIZADORA CLIENTES FICTICIA S.A.S.",
      "status": "ACTIVE"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

**Guardar:** `items[0].id` → `<ORG_EMPRESA>`

## 3. Consultar la persona cliente (ficticia) en Party Identity

> **Otro servicio:** esta llamada va a **Party Identity Service**, no a Commercial Relationship. No se ejecuta en la validación automática: su resultado se simula.

```http
GET http://localhost:8002/api/v1/person-identities?search=<documento>
```

**Permiso que exige la URL:** `perm:party-identity:person_identities:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:party-identity:person_identities:read`), `ventas.test` (por `perm:party-identity:person_identities:read`), `reportes.test` (por `perm:party-identity:person_identities:read`), `consulta.test` (por `perm:party-identity:person_identities:read`)
- ❌ **No pueden (responde `403`):** `inventario.test` — no tiene ningún permiso sobre `person_identities` de `party-identity`

**Por qué se hace así**

- Commercial Relationship **no guarda** nombres ni documentos: solo el `id` de la `PersonIdentity` (Principio III). Si la persona no existe, se registra primero en Party Identity.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "id": "<PERSONA>",
      "identification_type": "CC",
      "identification_number": "<documento oficial; dato ficticio aquí>",
      "first_name": "<nombre ficticio>",
      "status": "ACTIVE"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

**Guardar:** `items[0].id` → `<PERSONA>`

## 4. Consultar la organización MINIMARKET EJEMPLO FICTICIO S.A.S. en Party Identity

> **Otro servicio:** esta llamada va a **Party Identity Service**, no a Commercial Relationship. No se ejecuta en la validación automática: su resultado se simula.

```http
GET http://localhost:8002/api/v1/organization-identities?search=<NIT>
```

**Permiso que exige la URL:** `perm:party-identity:organization_identities:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:party-identity:organization_identities:read`), `ventas.test` (por `perm:party-identity:organization_identities:read`), `reportes.test` (por `perm:party-identity:organization_identities:read`), `consulta.test` (por `perm:party-identity:organization_identities:read`)
- ❌ **No pueden (responde `403`):** `inventario.test` — no tiene ningún permiso sobre `organization_identities` de `party-identity`

**Por qué se hace así**

- Commercial Relationship **no guarda** la razón social ni el NIT: solo el `id` de la `OrganizationIdentity` (Principio III). El NIT real se toma de una fuente oficial (RUT, RUES).

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "id": "<ORG_CLIENTE>",
      "identification_type": "NIT",
      "identification_number": "<NIT obtenido del RUT; dato ficticio aquí>",
      "legal_name": "MINIMARKET EJEMPLO FICTICIO S.A.S.",
      "status": "ACTIVE"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

**Guardar:** `items[0].id` → `<ORG_CLIENTE>`

## 5. Consultar la persona de contacto del minimarket (ficticia) en Party Identity

> **Otro servicio:** esta llamada va a **Party Identity Service**, no a Commercial Relationship. No se ejecuta en la validación automática: su resultado se simula.

```http
GET http://localhost:8002/api/v1/organization-identities/<ORG_CLIENTE>/contact-persons
```

**Permiso que exige la URL:** `perm:party-identity:organization_contact_persons:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:party-identity:organization_contact_persons:read`), `ventas.test` (por `perm:party-identity:organization_contact_persons:read`)
- ❌ **No pueden (responde `403`):** `inventario.test`, `reportes.test`, `consulta.test` — no tienen ningún permiso sobre `organization_contact_persons` de `party-identity`

**Por qué se hace así**

- El contacto preferido debe pertenecer a la misma organización y estar activo; el servicio lo valida en Party Identity al asignarlo (FR-022).

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "id": "<CONTACTO>",
      "organization_identity_id": "<ORG_CLIENTE>",
      "is_active": true,
      "position": "<cargo ficticio>"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

**Guardar:** `items[0].id` → `<CONTACTO>`

## 6. Consultar la organización DISTRIBUIDORA AJENA FICTICIA S.A.S. en Party Identity

> **Otro servicio:** esta llamada va a **Party Identity Service**, no a Commercial Relationship. No se ejecuta en la validación automática: su resultado se simula.

```http
GET http://localhost:8002/api/v1/organization-identities?search=<NIT>
```

**Permiso que exige la URL:** `perm:party-identity:organization_identities:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:party-identity:organization_identities:read`), `ventas.test` (por `perm:party-identity:organization_identities:read`), `reportes.test` (por `perm:party-identity:organization_identities:read`), `consulta.test` (por `perm:party-identity:organization_identities:read`)
- ❌ **No pueden (responde `403`):** `inventario.test` — no tiene ningún permiso sobre `organization_identities` de `party-identity`

**Por qué se hace así**

- Commercial Relationship **no guarda** la razón social ni el NIT: solo el `id` de la `OrganizationIdentity` (Principio III). El NIT real se toma de una fuente oficial (RUT, RUES).

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "id": "<ORG_OTRA>",
      "identification_type": "NIT",
      "identification_number": "<NIT obtenido del RUT; dato ficticio aquí>",
      "legal_name": "DISTRIBUIDORA AJENA FICTICIA S.A.S.",
      "status": "ACTIVE"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

**Guardar:** `items[0].id` → `<ORG_OTRA>`

## 7. Consultar la persona de contacto de la distribuidora (ficticia) en Party Identity

> **Otro servicio:** esta llamada va a **Party Identity Service**, no a Commercial Relationship. No se ejecuta en la validación automática: su resultado se simula.

```http
GET http://localhost:8002/api/v1/organization-identities/<ORG_OTRA>/contact-persons
```

**Permiso que exige la URL:** `perm:party-identity:organization_contact_persons:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:party-identity:organization_contact_persons:read`), `ventas.test` (por `perm:party-identity:organization_contact_persons:read`)
- ❌ **No pueden (responde `403`):** `inventario.test`, `reportes.test`, `consulta.test` — no tienen ningún permiso sobre `organization_contact_persons` de `party-identity`

**Por qué se hace así**

- El contacto preferido debe pertenecer a la misma organización y estar activo; el servicio lo valida en Party Identity al asignarlo (FR-022).

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "id": "<CONTACTO_OTRA>",
      "organization_identity_id": "<ORG_OTRA>",
      "is_active": true,
      "position": "<cargo ficticio>"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

**Guardar:** `items[0].id` → `<CONTACTO_OTRA>`

---

[Orden del ejercicio](ORDEN.md) · [Paso siguiente →](02-cliente-persona.md)
