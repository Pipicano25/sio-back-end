# Paso 05 de 05 — Retirar la regla

Ejercicio 1 — Reglas de identificación: crear, versionar y retirar · [← Paso anterior](04-nueva-version.md) · [Orden del ejercicio](ORDEN.md)

**Objetivo:** Dejar histórica la versión vigente, sin borrarla.

**Necesita (de pasos anteriores):** `<REGLA_PA_V2>` — pasos [04](04-nueva-version.md)

---

## 1. Retirar la versión vigente

```http
POST /api/v1/identification-type-rules/<REGLA_PA_V2>/deactivate
```

```json
{
  "version": 1
}
```

**Permiso que exige la URL:** `perm:party-identity:identification_type_rules:delete`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`)
- ❌ **No pueden (responde `403`):** `supervisor.test` — sobre `party-identity` solo tiene `create`, `read`, `update`; le falta `delete`; `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `party-identity` solo tienen `read`; les falta `delete`; `inventario.test` — no tiene ningún permiso sobre `party-identity`
- ℹ️ Retirar una regla (`POST .../deactivate`) exige `delete`, aunque no la elimina: queda histórica.

**Por qué se hace así**

- Retirar exige `delete` sobre `identification_type_rules`; la regla no se elimina (D7).
- Sin regla activa `PA`, las personas con esa sigla vuelven a validarse solo con las reglas base.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "id": "<REGLA_PA_V2>",
  "is_active": false,
  "version": 2
}
```

## 2. Intentar retirarla otra vez (rechazado)

```http
POST /api/v1/identification-type-rules/<REGLA_PA_V2>/deactivate
```

```json
{
  "version": 2
}
```

**Permiso que exige la URL:** `perm:party-identity:identification_type_rules:delete`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`)
- ❌ **No pueden (responde `403`):** `supervisor.test` — sobre `party-identity` solo tiene `create`, `read`, `update`; le falta `delete`; `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `party-identity` solo tienen `read`; les falta `delete`; `inventario.test` — no tiene ningún permiso sobre `party-identity`
- ℹ️ Retirar una regla (`POST .../deactivate`) exige `delete`, aunque no la elimina: queda histórica.

**Por qué se hace así**

- Una regla histórica no admite cambios: responde `409 INVALID_STATUS_TRANSITION`.

**Respuesta esperada (error) — `409 Conflict`** (abreviada)

```json
{
  "status": 409,
  "code": "PARTY_IDENTITY.INVALID_STATUS_TRANSITION"
}
```

---

[← Paso anterior](04-nueva-version.md) · [Orden del ejercicio](ORDEN.md)
