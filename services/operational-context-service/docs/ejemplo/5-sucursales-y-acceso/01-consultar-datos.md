# Paso 01 de 05 — Consultar la organización y la persona

Ejercicio 5 — Sucursales asignadas y acceso operativo · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](02-empresa-y-sucursales.md)

**Objetivo:** Obtener `<ORG_EMPRESA>` y `<PERSONA_COMPRADOR>`.

**Deja guardado para los siguientes pasos:** `<ORG_EMPRESA>`, `<PERSONA_COMPRADOR>`

---

## 1. Consultar la organización LOGÍSTICA ACCESO FICTICIA S.A.S. en Party Identity Service

> **Otro servicio:** esta llamada va a **Party Identity Service**, no a Operational Context. No se ejecuta en la validación automática: su resultado se simula.

```http
GET http://localhost:8002/api/v1/organization-identities?search=900
```

**Permiso que exige la URL:** `perm:party-identity:organization_identities:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:party-identity:organization_identities:read`), `ventas.test` (por `perm:party-identity:organization_identities:read`), `reportes.test` (por `perm:party-identity:organization_identities:read`), `consulta.test` (por `perm:party-identity:organization_identities:read`)
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
      "legal_name": "LOGÍSTICA ACCESO FICTICIA S.A.S.",
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

## 2. Consultar la persona del comprador (ficticio) en Party Identity Service

> **Otro servicio:** esta llamada va a **Party Identity Service**, no a Operational Context. No se ejecuta en la validación automática: su resultado se simula.

```http
GET http://localhost:8002/api/v1/person-identities?search=<documento>
```

**Permiso que exige la URL:** `perm:party-identity:person_identities:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:party-identity:person_identities:read`), `ventas.test` (por `perm:party-identity:person_identities:read`), `reportes.test` (por `perm:party-identity:person_identities:read`), `consulta.test` (por `perm:party-identity:person_identities:read`)
- ❌ **No pueden (responde `403`):** `inventario.test` — no tiene ningún permiso sobre `party-identity`

**Por qué se hace así**

- Operational Context **no guarda** nombres ni documentos de las personas: solo el `id` de su `PersonIdentity` en **Party Identity Service** (DS-16, Principio III).
- Si la persona no existe, se registra primero en Party Identity con sus datos oficiales.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "id": "<PERSONA_COMPRADOR>",
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

**Guardar:** `items[0].id` → `<PERSONA_COMPRADOR>`

---

[Orden del ejercicio](ORDEN.md) · [Paso siguiente →](02-empresa-y-sucursales.md)
