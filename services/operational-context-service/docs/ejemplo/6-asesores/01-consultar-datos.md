# Paso 01 de 05 — Consultar la organización y las personas

Ejercicio 6 — Asesores de la empresa · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](02-registrar-empresa.md)

**Objetivo:** Obtener `<ORG_EMPRESA>` y las tres personas.

**Deja guardado para los siguientes pasos:** `<ORG_EMPRESA>`, `<PERSONA_ASESOR_1>`, `<PERSONA_ASESOR_2>`, `<PERSONA_ASESOR_3>`

---

## 1. Consultar la organización ASESORADA EJEMPLO FICTICIA S.A.S. en Party Identity Service

> **Otro servicio:** esta llamada va a **Party Identity Service**, no a Operational Context. No se ejecuta en la validación automática: su resultado se simula.

```http
GET http://localhost:8002/api/v1/organization-identities?search=900
```

**Permiso que exige la URL:** `perm:party-identity:organization_identities:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:party-identity:all:read`), `ventas.test` (por `perm:party-identity:all:read`), `reportes.test` (por `perm:all:all:read`), `consulta.test` (por `perm:all:all:read`)
- ❌ **No pueden (responde `403`):** `inventario.test` — no tiene ningún permiso sobre `party-identity`

**Por qué se hace así**

- Operational Context **no guarda** la razón social, el nombre comercial ni el NIT de la empresa: solo el `id` de su identidad legal en **Party Identity Service** (DS-01, DS-13).
- Si la organización todavía no existe, se registra primero en Party Identity (`POST /api/v1/organization-identities`) con sus datos legales oficiales.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "id": "<ORG_EMPRESA>",
      "identification_type": "NIT",
      "identification_number": "<NIT obtenido del RUT; dato ficticio aquí>",
      "legal_name": "ASESORADA EJEMPLO FICTICIA S.A.S.",
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

## 2. Consultar la persona del primer asesor (ficticio) en Party Identity Service

> **Otro servicio:** esta llamada va a **Party Identity Service**, no a Operational Context. No se ejecuta en la validación automática: su resultado se simula.

```http
GET http://localhost:8002/api/v1/person-identities?search=<documento>
```

**Permiso que exige la URL:** `perm:party-identity:person_identities:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:party-identity:all:read`), `ventas.test` (por `perm:party-identity:all:read`), `reportes.test` (por `perm:all:all:read`), `consulta.test` (por `perm:all:all:read`)
- ❌ **No pueden (responde `403`):** `inventario.test` — no tiene ningún permiso sobre `party-identity`

**Por qué se hace así**

- Operational Context **no guarda** nombres ni documentos de las personas: solo el `id` de su `PersonIdentity` en **Party Identity Service** (DS-16, Principio III).
- Si la persona no existe, se registra primero en Party Identity con sus datos oficiales.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "id": "<PERSONA_ASESOR_1>",
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

**Guardar:** `items[0].id` → `<PERSONA_ASESOR_1>`

## 3. Consultar la persona del nuevo asesor (ficticio) en Party Identity Service

> **Otro servicio:** esta llamada va a **Party Identity Service**, no a Operational Context. No se ejecuta en la validación automática: su resultado se simula.

```http
GET http://localhost:8002/api/v1/person-identities?search=<documento>
```

**Permiso que exige la URL:** `perm:party-identity:person_identities:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:party-identity:all:read`), `ventas.test` (por `perm:party-identity:all:read`), `reportes.test` (por `perm:all:all:read`), `consulta.test` (por `perm:all:all:read`)
- ❌ **No pueden (responde `403`):** `inventario.test` — no tiene ningún permiso sobre `party-identity`

**Por qué se hace así**

- Operational Context **no guarda** nombres ni documentos de las personas: solo el `id` de su `PersonIdentity` en **Party Identity Service** (DS-16, Principio III).
- Si la persona no existe, se registra primero en Party Identity con sus datos oficiales.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "id": "<PERSONA_ASESOR_2>",
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

**Guardar:** `items[0].id` → `<PERSONA_ASESOR_2>`

## 4. Consultar la persona del asesor no principal (ficticio) en Party Identity Service

> **Otro servicio:** esta llamada va a **Party Identity Service**, no a Operational Context. No se ejecuta en la validación automática: su resultado se simula.

```http
GET http://localhost:8002/api/v1/person-identities?search=<documento>
```

**Permiso que exige la URL:** `perm:party-identity:person_identities:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:party-identity:all:read`), `ventas.test` (por `perm:party-identity:all:read`), `reportes.test` (por `perm:all:all:read`), `consulta.test` (por `perm:all:all:read`)
- ❌ **No pueden (responde `403`):** `inventario.test` — no tiene ningún permiso sobre `party-identity`

**Por qué se hace así**

- Operational Context **no guarda** nombres ni documentos de las personas: solo el `id` de su `PersonIdentity` en **Party Identity Service** (DS-16, Principio III).
- Si la persona no existe, se registra primero en Party Identity con sus datos oficiales.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "id": "<PERSONA_ASESOR_3>",
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

**Guardar:** `items[0].id` → `<PERSONA_ASESOR_3>`

---

[Orden del ejercicio](ORDEN.md) · [Paso siguiente →](02-registrar-empresa.md)
