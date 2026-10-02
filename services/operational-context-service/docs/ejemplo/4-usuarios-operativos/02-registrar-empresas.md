# Paso 02 de 05 — Registrar las dos empresas

Ejercicio 4 — Usuarios operativos de una empresa · [← Paso anterior](01-consultar-personas.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](03-registrar-usuarios.md)

**Objetivo:** Crear las empresas A y B (solo el administrador de plataforma).

**Deja guardado para los siguientes pasos:** `<ORG_A>`, `<ORG_B>`, `<EMPRESA_A>`, `<EMPRESA_B>`

---

## 1. Consultar la organización COMERCIALIZADORA USUARIOS FICTICIA S.A.S. en Party Identity Service

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
      "id": "<ORG_A>",
      "identification_type": "NIT",
      "identification_number": "<NIT obtenido del RUT; dato ficticio aquí>",
      "legal_name": "COMERCIALIZADORA USUARIOS FICTICIA S.A.S.",
      "status": "ACTIVE"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

**Guardar:** `items[0].id` → `<ORG_A>`

## 2. Consultar la organización ALIADO USUARIOS FICTICIO S.A.S. en Party Identity Service

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
      "id": "<ORG_B>",
      "identification_type": "NIT",
      "identification_number": "<NIT obtenido del RUT; dato ficticio aquí>",
      "legal_name": "ALIADO USUARIOS FICTICIO S.A.S.",
      "status": "ACTIVE"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

**Guardar:** `items[0].id` → `<ORG_B>`

## 3. Registrar la empresa A

```http
POST /api/v1/companies
```

```json
{
  "organization_identity_id": "<ORG_A>"
}
```

**Permisos que exige la URL (todos):** `perm:operational-context:companies:create` + `perm:operational-context:platform:administer`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`)
- ❌ **No pueden (responde `403`):** `supervisor.test` — sobre `operational-context` solo tiene `create`, `read`, `update`; le falta `administer`; `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `operational-context` solo tienen `read`; les falta `create`
- ℹ️ Para registrar o cambiar la organización o la ubicación, el token del usuario debe poder además **leer** en Party Identity y Geography: el servicio valida esas referencias con el mismo token. `administradores` y `supervisores` tienen esa lectura.
- ℹ️ Alcance de plataforma (Fase B, DS-05): registrar, inactivar y reactivar empresas y ver todas las empresas sin ser miembro. Solo lo concede `perm:all:all:all` (`administradores`); los comodines de lectura, creación o modificación **no** lo conceden.

**Por qué se hace así**

- Registrar empresas exige `platform:administer` (Fase B): solo `admin.test`.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<EMPRESA_A>",
  "status": "ACTIVE"
}
```

**Guardar:** `id` → `<EMPRESA_A>`

## 4. Registrar la empresa B

```http
POST /api/v1/companies
```

```json
{
  "organization_identity_id": "<ORG_B>"
}
```

**Permisos que exige la URL (todos):** `perm:operational-context:companies:create` + `perm:operational-context:platform:administer`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`)
- ❌ **No pueden (responde `403`):** `supervisor.test` — sobre `operational-context` solo tiene `create`, `read`, `update`; le falta `administer`; `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `operational-context` solo tienen `read`; les falta `create`
- ℹ️ Para registrar o cambiar la organización o la ubicación, el token del usuario debe poder además **leer** en Party Identity y Geography: el servicio valida esas referencias con el mismo token. `administradores` y `supervisores` tienen esa lectura.
- ℹ️ Alcance de plataforma (Fase B, DS-05): registrar, inactivar y reactivar empresas y ver todas las empresas sin ser miembro. Solo lo concede `perm:all:all:all` (`administradores`); los comodines de lectura, creación o modificación **no** lo conceden.

**Por qué se hace así**

- Segunda empresa para mostrar la misma persona en dos empresas.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<EMPRESA_B>",
  "status": "ACTIVE"
}
```

**Guardar:** `id` → `<EMPRESA_B>`

---

[← Paso anterior](01-consultar-personas.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](03-registrar-usuarios.md)
