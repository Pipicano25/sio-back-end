# Paso 02 de 03 — Registrar la organización

Ejercicio 3 — Organizaciones: registrar, rechazos, inactivar y reactivar · [← Paso anterior](01-consultar-pais.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](03-inactivar-y-reactivar.md)

**Objetivo:** Crear la organización y comprobar los rechazos.

**Necesita (de pasos anteriores):** `<PAIS_CO>` — pasos [01](01-consultar-pais.md)

**Deja guardado para los siguientes pasos:** `<ORG_EJEMPLO>`

---

## 1. Registrar la organización con NIT

```http
POST /api/v1/organization-identities
```

```json
{
  "country_id": "<PAIS_CO>",
  "identification_type": "NIT",
  "identification_number": "900000001-1",
  "legal_name": "COMERCIALIZADORA EJEMPLO FICTICIA S.A.S.",
  "trade_name": "EJEMPLO FICTICIO",
  "organization_type": "SAS",
  "registration_status": "ACTIVA"
}
```

**Permiso que exige la URL:** `perm:party-identity:organization_identities:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `party-identity` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `party-identity`

**Por qué se hace así**

- `identification_type: NIT` es la sigla; el número va con guion y dígito de verificación.
- `trade_name`, `organization_type`, `registration_status` y `website` son opcionales.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<ORG_EJEMPLO>",
  "identification_type": "NIT",
  "identification_number": "900000001-1",
  "legal_name": "COMERCIALIZADORA EJEMPLO FICTICIA S.A.S.",
  "registration_status": "ACTIVA",
  "status": "ACTIVE",
  "version": 1
}
```

**Guardar:** `id` → `<ORG_EJEMPLO>`

## 2. Intentar registrar un NIT sin dígito de verificación (rechazado)

```http
POST /api/v1/organization-identities
```

```json
{
  "country_id": "<PAIS_CO>",
  "identification_type": "NIT",
  "identification_number": "900000001",
  "legal_name": "COMERCIALIZADORA EJEMPLO FICTICIA S.A.S.",
  "trade_name": "EJEMPLO FICTICIO",
  "organization_type": "SAS",
  "registration_status": "ACTIVA"
}
```

**Permiso que exige la URL:** `perm:party-identity:organization_identities:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `party-identity` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `party-identity`

**Por qué se hace así**

- No cumple la regla `NIT`: responde `422 INVALID_IDENTIFICATION_NUMBER` con la descripción de la regla.

**Respuesta esperada (error) — `422 Unprocessable Content`** (abreviada)

```json
{
  "status": 422,
  "code": "PARTY_IDENTITY.INVALID_IDENTIFICATION_NUMBER",
  "detail": "El número de identificación no cumple ninguna regla activa para la sigla indicada. Numero de Identificacion Tributaria de organizacion: base alfanumerica de 4 a 11 caracteres, guion y digito de verificacion."
}
```

## 3. Intentar registrar con un país inexistente (rechazado)

```http
POST /api/v1/organization-identities
```

```json
{
  "country_id": "5e0c0f6e-0000-4000-8000-00000000dead",
  "identification_type": "NIT",
  "identification_number": "900000002-2",
  "legal_name": "COMERCIALIZADORA EJEMPLO FICTICIA S.A.S.",
  "trade_name": "EJEMPLO FICTICIO",
  "organization_type": "SAS",
  "registration_status": "ACTIVA"
}
```

**Permiso que exige la URL:** `perm:party-identity:organization_identities:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `party-identity` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `party-identity`

**Por qué se hace así**

- Geography responde que el país no existe: `422 COUNTRY_NOT_FOUND`; no se guarda nada.

**Respuesta esperada (error) — `422 Unprocessable Content`** (abreviada)

```json
{
  "status": 422,
  "code": "PARTY_IDENTITY.COUNTRY_NOT_FOUND"
}
```

---

[← Paso anterior](01-consultar-pais.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](03-inactivar-y-reactivar.md)
