# Paso 03 de 05 — Corregir la descripción

Ejercicio 1 — Reglas de identificación: crear, versionar y retirar · [← Paso anterior](02-crear-regla.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](04-nueva-version.md)

**Objetivo:** Modificar en sitio lo que no cambia la validación.

**Necesita (de pasos anteriores):** `<REGLA_PA>` — pasos [02](02-crear-regla.md)

---

## 1. Corregir la descripción y el ejemplo

```http
PUT /api/v1/identification-type-rules/<REGLA_PA>
```

```json
{
  "number_pattern_description": "Pasaporte colombiano: 6 a 9 letras o dígitos, sin espacios.",
  "example_value": "AB123456",
  "version": 1
}
```

**Permiso que exige la URL:** `perm:party-identity:identification_type_rules:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `party-identity` solo tienen `read`; les falta `update`; `inventario.test` — no tiene ningún permiso sobre `party-identity`

**Por qué se hace así**

- El `PUT` solo cambia la descripción y el ejemplo. Enviar otro `number_pattern` o edades responde `422 RULE_CHANGE_REQUIRES_NEW_VERSION`, y cambiar país, tipo o sigla `422 IMMUTABLE_FIELD`.
- `version` es la que se leyó; si otro usuario la cambió antes, responde `409 VERSION_CONFLICT`.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "id": "<REGLA_PA>",
  "number_pattern_description": "Pasaporte colombiano: 6 a 9 letras o dígitos, sin espacios.",
  "version": 2,
  "is_active": true
}
```

## 2. Intentar cambiar el patrón con `PUT` (rechazado)

```http
PUT /api/v1/identification-type-rules/<REGLA_PA>
```

```json
{
  "number_pattern_description": "Pasaporte colombiano: 6 a 9 letras o dígitos, sin espacios.",
  "example_value": "AB123456",
  "number_pattern": "^[A-Z]{2}[0-9]{6,7}$",
  "version": 2
}
```

**Permiso que exige la URL:** `perm:party-identity:identification_type_rules:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `party-identity` solo tienen `read`; les falta `update`; `inventario.test` — no tiene ningún permiso sobre `party-identity`

**Por qué se hace así**

- Cambiar el patrón exige una nueva versión (paso siguiente).

**Respuesta esperada (error) — `422 Unprocessable Content`** (abreviada)

```json
{
  "status": 422,
  "code": "PARTY_IDENTITY.RULE_CHANGE_REQUIRES_NEW_VERSION"
}
```

---

[← Paso anterior](02-crear-regla.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](04-nueva-version.md)
