# Paso 02 de 04 — Registrar la persona

Ejercicio 2 — Personas: registrar, validar, verificar e inactivar · [← Paso anterior](01-consultar-pais.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](03-verificar-persona.md)

**Objetivo:** Crear la persona y comprobar los rechazos por edad y por duplicado.

**Necesita (de pasos anteriores):** `<PAIS_CO>` — pasos [01](01-consultar-pais.md)

**Deja guardado para los siguientes pasos:** `<PERSONA_ANA>`

---

## 1. Registrar a ANA MARIA con cédula

```http
POST /api/v1/person-identities
```

```json
{
  "identification_country_id": "<PAIS_CO>",
  "identification_type": "CC",
  "identification_number": "1000000001",
  "first_name": "ANA",
  "middle_name": "MARIA",
  "last_name": "EJEMPLO",
  "second_last_name": "FICTICIA",
  "birth_date": "1990-05-10"
}
```

**Permiso que exige la URL:** `perm:party-identity:person_identities:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `party-identity` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `party-identity`

**Por qué se hace así**

- `identification_type` es la **sigla** (`CC`); se normaliza a mayúsculas y el número sin espacios exteriores.
- No se envía `verification_status`: queda `UNVERIFIED`. Tampoco `status` ni campos de auditoría (`created_by` se toma del token); enviarlos responde `422`.
- El servicio valida el país contra Geography y el número y la edad contra las reglas activas.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<PERSONA_ANA>",
  "identification_type": "CC",
  "identification_number": "1000000001",
  "first_name": "ANA",
  "last_name": "EJEMPLO",
  "verification_status": "UNVERIFIED",
  "status": "ACTIVE",
  "version": 1
}
```

**Guardar:** `id` → `<PERSONA_ANA>`

## 2. Intentar registrar con tarjeta de identidad (`TI`) a una persona adulta (rechazado)

```http
POST /api/v1/person-identities
```

```json
{
  "identification_country_id": "<PAIS_CO>",
  "identification_type": "TI",
  "identification_number": "1000000002",
  "first_name": "LUIS",
  "middle_name": null,
  "last_name": "EJEMPLO",
  "second_last_name": "FICTICIA",
  "birth_date": "1990-05-10"
}
```

**Permiso que exige la URL:** `perm:party-identity:person_identities:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `party-identity` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `party-identity`

**Por qué se hace así**

- La regla `TI` exige de 7 a 17 años; con nacimiento en 1990 responde `422 AGE_OUT_OF_RANGE`.

**Respuesta esperada (error) — `422 Unprocessable Content`** (abreviada)

```json
{
  "status": 422,
  "code": "PARTY_IDENTITY.AGE_OUT_OF_RANGE",
  "detail": "La edad de la persona no cumple el rango permitido para el tipo de identificación."
}
```

## 3. Intentar registrar otra vez la misma cédula (rechazado)

```http
POST /api/v1/person-identities
```

```json
{
  "identification_country_id": "<PAIS_CO>",
  "identification_type": "CC",
  "identification_number": "1000000001",
  "first_name": "OTRA",
  "middle_name": "MARIA",
  "last_name": "EJEMPLO",
  "second_last_name": "FICTICIA",
  "birth_date": "1990-05-10"
}
```

**Permiso que exige la URL:** `perm:party-identity:person_identities:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `party-identity` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `party-identity`

**Por qué se hace así**

- País + tipo + número es único, también frente a personas inactivas: responde `409`. El mensaje no muestra el número completo.

**Respuesta esperada (error) — `409 Conflict`** (abreviada)

```json
{
  "status": 409,
  "code": "PARTY_IDENTITY.DUPLICATE_IDENTIFICATION",
  "detail": "Ya existe una identidad con el país, tipo y número de identificación indicados."
}
```

---

[← Paso anterior](01-consultar-pais.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](03-verificar-persona.md)
