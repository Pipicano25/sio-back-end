# Paso 01 de 05 — Consultar las personas en Party Identity

Ejercicio 4 — Usuarios operativos de una empresa · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](02-registrar-empresas.md)

**Objetivo:** Obtener `<PERSONA_SUPERVISORA>` y `<PERSONA_COMPRADOR>`.

**Deja guardado para los siguientes pasos:** `<PERSONA_SUPERVISORA>`, `<PERSONA_COMPRADOR>`

---

## 1. Consultar la persona de la supervisora (ficticia) en Party Identity Service

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
      "id": "<PERSONA_SUPERVISORA>",
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

**Guardar:** `items[0].id` → `<PERSONA_SUPERVISORA>`

## 2. Consultar la persona del comprador (ficticio) en Party Identity Service

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

[Orden del ejercicio](ORDEN.md) · [Paso siguiente →](02-registrar-empresas.md)
