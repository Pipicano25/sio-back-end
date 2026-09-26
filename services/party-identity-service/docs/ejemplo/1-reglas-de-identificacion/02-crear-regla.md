# Paso 02 de 05 — Crear la regla de pasaporte

Ejercicio 1 — Reglas de identificación: crear, versionar y retirar · [← Paso anterior](01-consultar-pais-y-reglas.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](03-corregir-descripcion.md)

**Objetivo:** Crear la regla `PASSPORT` / `PA` y comprobar los rechazos.

**Necesita (de pasos anteriores):** `<PAIS_CO>` — pasos [01](01-consultar-pais-y-reglas.md)

**Deja guardado para los siguientes pasos:** `<REGLA_PA>`

---

## 1. Crear la regla `PASSPORT` (`PA`)

```http
POST /api/v1/identification-type-rules
```

```json
{
  "party_kind": "PERSON",
  "country_id": "<PAIS_CO>",
  "identification_type": "PASSPORT",
  "sigla": "PA",
  "number_pattern": "^[A-Z0-9]{6,9}$",
  "number_pattern_description": "Pasaporte: 6 a 9 letras o dígitos.",
  "example_value": "AB123456"
}
```

**Permiso que exige la URL:** `perm:party-identity:identification_type_rules:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `party-identity` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `party-identity`
- ℹ️ Crear una **nueva versión** de una regla (`POST .../versions`) también exige `create`: el resultado es una regla nueva.

**Por qué se hace así**

- `identification_type` es el formato concreto; `sigla` es lo que se escribe al registrar la persona.
- `example_value` debe cumplir el patrón: si no, responde `422 EXAMPLE_DOES_NOT_MATCH_PATTERN`.
- No se envían edades: el pasaporte no restringe la edad.
- El servicio valida `<PAIS_CO>` contra Geography antes de guardar.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<REGLA_PA>",
  "party_kind": "PERSON",
  "identification_type": "PASSPORT",
  "sigla": "PA",
  "number_pattern": "^[A-Z0-9]{6,9}$",
  "min_age_years": null,
  "max_age_years": null,
  "is_active": true,
  "valid_to": null,
  "version": 1
}
```

**Guardar:** `id` → `<REGLA_PA>`

## 2. Intentar crear otra regla activa igual (rechazado)

```http
POST /api/v1/identification-type-rules
```

```json
{
  "party_kind": "PERSON",
  "country_id": "<PAIS_CO>",
  "identification_type": "PASSPORT",
  "sigla": "PA",
  "number_pattern": "^[A-Z0-9]{6,9}$",
  "number_pattern_description": "Duplicado."
}
```

**Permiso que exige la URL:** `perm:party-identity:identification_type_rules:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `party-identity` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `party-identity`
- ℹ️ Crear una **nueva versión** de una regla (`POST .../versions`) también exige `create`: el resultado es una regla nueva.

**Por qué se hace así**

- Solo puede haber **una** regla activa por tipo de parte + país + tipo de identificación.

**Respuesta esperada (error) — `409 Conflict`** (abreviada)

```json
{
  "status": 409,
  "code": "PARTY_IDENTITY.DUPLICATE_ACTIVE_RULE",
  "detail": "Ya existe una regla activa para el tipo de parte, país y tipo de identificación indicados."
}
```

## 3. Intentar crear una regla con un patrón inválido (rechazado)

```http
POST /api/v1/identification-type-rules
```

```json
{
  "party_kind": "PERSON",
  "country_id": "<PAIS_CO>",
  "identification_type": "DIPLOMATIC_ID",
  "sigla": "CD",
  "number_pattern": "^[0-9{5}$",
  "number_pattern_description": "Patrón mal escrito."
}
```

**Permiso que exige la URL:** `perm:party-identity:identification_type_rules:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `party-identity` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `party-identity`
- ℹ️ Crear una **nueva versión** de una regla (`POST .../versions`) también exige `create`: el resultado es una regla nueva.

**Por qué se hace así**

- El patrón es una expresión regular; si no compila responde `422 INVALID_NUMBER_PATTERN`.

**Respuesta esperada (error) — `422 Unprocessable Content`** (abreviada)

```json
{
  "status": 422,
  "code": "PARTY_IDENTITY.INVALID_NUMBER_PATTERN"
}
```

---

[← Paso anterior](01-consultar-pais-y-reglas.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](03-corregir-descripcion.md)
