# Paso 04 de 05 — Crear una nueva versión de la regla

Ejercicio 1 — Reglas de identificación: crear, versionar y retirar · [← Paso anterior](03-corregir-descripcion.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](05-retirar-regla.md)

**Objetivo:** Cambiar el patrón conservando la regla anterior como histórica.

**Necesita (de pasos anteriores):** `<REGLA_PA>` — pasos [02](02-crear-regla.md)

**Deja guardado para los siguientes pasos:** `<REGLA_PA_V2>`

---

## 1. Crear la nueva versión con el patrón corregido

```http
POST /api/v1/identification-type-rules/<REGLA_PA>/versions
```

```json
{
  "number_pattern": "^[A-Z]{2}[0-9]{6,7}$",
  "number_pattern_description": "Pasaporte: 2 letras y 6 o 7 dígitos.",
  "example_value": "AB123456",
  "version": 2
}
```

**Permiso que exige la URL:** `perm:party-identity:identification_type_rules:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `party-identity` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `party-identity`
- ℹ️ Crear una **nueva versión** de una regla (`POST .../versions`) también exige `create`: el resultado es una regla nueva.

**Por qué se hace así**

- En una sola transacción la regla actual queda histórica y se crea la nueva, activa.
- La nueva regla conserva país, tipo y sigla; tiene su propio `id`.
- Exige `create` sobre `identification_type_rules` (es una regla nueva), no `update`.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<REGLA_PA_V2>",
  "party_kind": "PERSON",
  "identification_type": "PASSPORT",
  "sigla": "PA",
  "number_pattern": "^[A-Z]{2}[0-9]{6,7}$",
  "min_age_years": null,
  "max_age_years": null,
  "is_active": true,
  "valid_to": null,
  "version": 1
}
```

**Guardar:** `id` → `<REGLA_PA_V2>`

## 2. Consultar la regla anterior

```http
GET /api/v1/identification-type-rules/<REGLA_PA>
```

**Permiso que exige la URL:** `perm:party-identity:identification_type_rules:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:party-identity:identification_type_rules:read`), `ventas.test` (por `perm:party-identity:identification_type_rules:read`), `reportes.test` (por `perm:party-identity:identification_type_rules:read`), `consulta.test` (por `perm:party-identity:identification_type_rules:read`)
- ❌ **No pueden (responde `403`):** `inventario.test` — no tiene ningún permiso sobre `party-identity`

**Por qué se hace así**

- Sigue existiendo, ahora histórica: `is_active: false` y `valid_to` con la fecha del cambio.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "id": "<REGLA_PA>",
  "number_pattern": "^[A-Z0-9]{6,9}$",
  "is_active": false,
  "version": 3
}
```

---

[← Paso anterior](03-corregir-descripcion.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](05-retirar-regla.md)
