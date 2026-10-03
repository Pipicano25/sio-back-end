# Paso 04 de 05 — Asignar sectores a una organización

Ejercicio 7 — Sectores económicos: árbol CIIU, catálogo propio y sectores de una organización · [← Paso anterior](03-consultar-pais.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](05-cerrar-asignacion.md)

**Objetivo:** Registrar la organización, asignar dos sectores y cambiar el principal.

**Necesita (de pasos anteriores):** `<PAIS_CO>`, `<CLASE_CAFE>`, `<CLASE_TIENDA>` — pasos [01](01-recorrer-arbol-ciiu.md), [03](03-consultar-pais.md)

**Deja guardado para los siguientes pasos:** `<ORG_CAFE>`, `<ASIG_CAFE>`, `<ASIG_TIENDA>`

---

## 1. Registrar la organización

```http
POST /api/v1/organization-identities
```

```json
{
  "country_id": "<PAIS_CO>",
  "identification_type": "NIT",
  "identification_number": "900000007-7",
  "legal_name": "CAFE Y TIENDA FICTICIA S.A.S."
}
```

**Permiso que exige la URL:** `perm:party-identity:organization_identities:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `party-identity` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `party-identity`

**Por qué se hace así**

- Las personas de contacto, sectores y representantes cuelgan de una organización `ACTIVE` de Party Identity; se registra primero con datos **ficticios** (NIT que cumple la regla `NIT`, no es real).

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<ORG_CAFE>",
  "legal_name": "CAFE Y TIENDA FICTICIA S.A.S.",
  "status": "ACTIVE"
}
```

**Guardar:** `id` → `<ORG_CAFE>`

## 2. Asignar la clase 0123 como sector principal

```http
POST /api/v1/organization-identities/<ORG_CAFE>/business-sectors
```

```json
{
  "global_business_sector_id": "<CLASE_CAFE>",
  "is_primary": true
}
```

**Permiso que exige la URL:** `perm:party-identity:organization_business_sectors:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `party-identity` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `party-identity`

**Por qué se hace así**

- Sin `valid_from`, la vigencia empieza ahora.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<ASIG_CAFE>",
  "global_business_sector_id": "<CLASE_CAFE>",
  "is_primary": true,
  "is_active": true,
  "valid_to": null,
  "version": 1
}
```

**Guardar:** `id` → `<ASIG_CAFE>`

## 3. Asignar la clase 4711 como sector secundario

```http
POST /api/v1/organization-identities/<ORG_CAFE>/business-sectors
```

```json
{
  "global_business_sector_id": "<CLASE_TIENDA>",
  "is_primary": false
}
```

**Permiso que exige la URL:** `perm:party-identity:organization_business_sectors:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `party-identity` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `party-identity`

**Por qué se hace así**

- Una organización puede tener varios sectores vigentes; solo uno es principal.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<ASIG_TIENDA>",
  "global_business_sector_id": "<CLASE_TIENDA>",
  "is_primary": false,
  "is_active": true,
  "valid_to": null,
  "version": 1
}
```

**Guardar:** `id` → `<ASIG_TIENDA>`

## 4. Intentar asignar otra vez la clase 4711 (rechazado)

```http
POST /api/v1/organization-identities/<ORG_CAFE>/business-sectors
```

```json
{
  "global_business_sector_id": "<CLASE_TIENDA>",
  "is_primary": false
}
```

**Permiso que exige la URL:** `perm:party-identity:organization_business_sectors:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `party-identity` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `party-identity`

**Por qué se hace así**

- Ya hay una asignación vigente de ese sector: `409 DUPLICATE_ACTIVE_SECTOR_ASSIGNMENT`.

**Respuesta esperada (error) — `409 Conflict`** (abreviada)

```json
{
  "status": 409,
  "code": "PARTY_IDENTITY.DUPLICATE_ACTIVE_SECTOR_ASSIGNMENT"
}
```

## 5. Cambiar el sector principal a 4711

```http
POST /api/v1/organization-business-sectors/<ASIG_TIENDA>:set-primary
```

```json
{
  "version": 1
}
```

**Permiso que exige la URL:** `perm:party-identity:organization_business_sectors:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `party-identity` solo tienen `read`; les falta `update`; `inventario.test` — no tiene ningún permiso sobre `party-identity`

**Por qué se hace así**

- Desmarca el principal anterior (su `version` también aumenta) en la misma transacción.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "id": "<ASIG_TIENDA>",
  "global_business_sector_id": "<CLASE_TIENDA>",
  "is_primary": true,
  "is_active": true,
  "valid_to": null,
  "version": 2
}
```

---

[← Paso anterior](03-consultar-pais.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](05-cerrar-asignacion.md)
