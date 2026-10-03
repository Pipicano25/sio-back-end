# Paso 05 de 05 — Cerrar una asignación y ver el historial

Ejercicio 7 — Sectores económicos: árbol CIIU, catálogo propio y sectores de una organización · [← Paso anterior](04-asignar-sectores.md) · [Orden del ejercicio](ORDEN.md)

**Objetivo:** Cerrar el sector 0123 y consultar las asignaciones.

**Necesita (de pasos anteriores):** `<ASIG_CAFE>`, `<ORG_CAFE>` — pasos [04](04-asignar-sectores.md)

---

## 1. Cerrar la asignación de la clase 0123

```http
POST /api/v1/organization-business-sectors/<ASIG_CAFE>:close
```

```json
{
  "version": 2
}
```

**Permiso que exige la URL:** `perm:party-identity:organization_business_sectors:delete`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`)
- ❌ **No pueden (responde `403`):** `supervisor.test` — sobre `party-identity` solo tiene `create`, `read`, `update`; le falta `delete`; `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `party-identity` solo tienen `read`; les falta `delete`; `inventario.test` — no tiene ningún permiso sobre `party-identity`

**Por qué se hace así**

- Exige `delete`; no borra: guarda `valid_to`.
- `version` es 2 porque `set-primary` la desmarcó como principal.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "id": "<ASIG_CAFE>",
  "global_business_sector_id": "<CLASE_CAFE>",
  "is_primary": false,
  "is_active": false,
  "valid_to": "<fecha y hora del cambio>",
  "version": 3
}
```

## 2. Consultar los sectores vigentes

```http
GET /api/v1/organization-identities/<ORG_CAFE>/business-sectors
```

**Permiso que exige la URL:** `perm:party-identity:organization_business_sectors:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:party-identity:organization_business_sectors:read`), `ventas.test` (por `perm:party-identity:organization_business_sectors:read`), `reportes.test` (por `perm:party-identity:organization_business_sectors:read`), `consulta.test` (por `perm:party-identity:organization_business_sectors:read`)
- ❌ **No pueden (responde `403`):** `inventario.test` — no tiene ningún permiso sobre `party-identity`

**Por qué se hace así**

- `state` omitido equivale a `active`.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "total_records": 1
}
```

## 3. Consultar el historial completo

```http
GET /api/v1/organization-identities/<ORG_CAFE>/business-sectors?state=all
```

**Permiso que exige la URL:** `perm:party-identity:organization_business_sectors:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:party-identity:organization_business_sectors:read`), `ventas.test` (por `perm:party-identity:organization_business_sectors:read`), `reportes.test` (por `perm:party-identity:organization_business_sectors:read`), `consulta.test` (por `perm:party-identity:organization_business_sectors:read`)
- ❌ **No pueden (responde `403`):** `inventario.test` — no tiene ningún permiso sobre `party-identity`

**Por qué se hace así**

- `state=active`, `closed` o `all`. Una asignación cerrada no se reactiva.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "total_records": 2
}
```

---

[← Paso anterior](04-asignar-sectores.md) · [Orden del ejercicio](ORDEN.md)
