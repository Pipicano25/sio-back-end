# Paso 02 de 05 — Crear sectores en una clasificación propia

Ejercicio 7 — Sectores económicos: árbol CIIU, catálogo propio y sectores de una organización · [← Paso anterior](01-recorrer-arbol-ciiu.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](03-consultar-pais.md)

**Objetivo:** Crear un sector con un hijo y ver el rechazo al inactivar el padre.

**Necesita (de pasos anteriores):** `<SECCION_A>` — pasos [01](01-recorrer-arbol-ciiu.md)

**Deja guardado para los siguientes pasos:** `<SECTOR_X>`, `<SECTOR_X1>`

---

## 1. Crear el sector raíz X

```http
POST /api/v1/global-business-sectors
```

```json
{
  "classification_system": "ejemplo_interno",
  "code": " x ",
  "name": "Sector interno X"
}
```

**Permiso que exige la URL:** `perm:party-identity:global_business_sectors:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `party-identity` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `party-identity`

**Por qué se hace así**

- `classification_system` y `code` se normalizan a mayúsculas sin espacios exteriores.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<SECTOR_X>",
  "classification_system": "EJEMPLO_INTERNO",
  "code": "X",
  "name": "Sector interno X",
  "parent_sector_id": null,
  "status": "ACTIVE",
  "version": 1
}
```

**Guardar:** `id` → `<SECTOR_X>`

## 2. Crear el sector X1, hijo de X

```http
POST /api/v1/global-business-sectors
```

```json
{
  "classification_system": "EJEMPLO_INTERNO",
  "code": "X1",
  "name": "Subsector interno X1",
  "parent_sector_id": "<SECTOR_X>"
}
```

**Permiso que exige la URL:** `perm:party-identity:global_business_sectors:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `party-identity` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `party-identity`

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<SECTOR_X1>",
  "classification_system": "EJEMPLO_INTERNO",
  "code": "X1",
  "name": "Subsector interno X1",
  "parent_sector_id": "<SECTOR_X>",
  "status": "ACTIVE",
  "version": 1
}
```

**Guardar:** `id` → `<SECTOR_X1>`

## 3. Intentar colgar X1 de un sector CIIU (rechazado)

```http
PUT /api/v1/global-business-sectors/<SECTOR_X1>
```

```json
{
  "name": "Subsector interno X1",
  "parent_sector_id": "<SECCION_A>",
  "version": 1
}
```

**Permiso que exige la URL:** `perm:party-identity:global_business_sectors:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `party-identity` solo tienen `read`; les falta `update`; `inventario.test` — no tiene ningún permiso sobre `party-identity`

**Por qué se hace así**

- El padre debe ser de la misma clasificación: `422 INVALID_SECTOR_HIERARCHY`.

**Respuesta esperada (error) — `422 Unprocessable Content`** (abreviada)

```json
{
  "status": 422,
  "code": "PARTY_IDENTITY.INVALID_SECTOR_HIERARCHY"
}
```

## 4. Intentar inactivar X con un hijo activo (rechazado)

```http
POST /api/v1/global-business-sectors/<SECTOR_X>:deactivate
```

```json
{
  "version": 1
}
```

**Permiso que exige la URL:** `perm:party-identity:global_business_sectors:delete`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`)
- ❌ **No pueden (responde `403`):** `supervisor.test` — sobre `party-identity` solo tiene `create`, `read`, `update`; le falta `delete`; `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `party-identity` solo tienen `read`; les falta `delete`; `inventario.test` — no tiene ningún permiso sobre `party-identity`

**Por qué se hace así**

- `409 SECTOR_HAS_ACTIVE_CHILDREN`: primero se inactiva X1; no hay cascada.

**Respuesta esperada (error) — `409 Conflict`** (abreviada)

```json
{
  "status": 409,
  "code": "PARTY_IDENTITY.SECTOR_HAS_ACTIVE_CHILDREN"
}
```

## 5. Inactivar X1

```http
POST /api/v1/global-business-sectors/<SECTOR_X1>:deactivate
```

```json
{
  "version": 1
}
```

**Permiso que exige la URL:** `perm:party-identity:global_business_sectors:delete`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`)
- ❌ **No pueden (responde `403`):** `supervisor.test` — sobre `party-identity` solo tiene `create`, `read`, `update`; le falta `delete`; `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `party-identity` solo tienen `read`; les falta `delete`; `inventario.test` — no tiene ningún permiso sobre `party-identity`

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "id": "<SECTOR_X1>",
  "classification_system": "EJEMPLO_INTERNO",
  "code": "X1",
  "name": "Subsector interno X1",
  "parent_sector_id": "<SECTOR_X>",
  "status": "INACTIVE",
  "version": 2
}
```

## 6. Inactivar X

```http
POST /api/v1/global-business-sectors/<SECTOR_X>:deactivate
```

```json
{
  "version": 1
}
```

**Permiso que exige la URL:** `perm:party-identity:global_business_sectors:delete`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`)
- ❌ **No pueden (responde `403`):** `supervisor.test` — sobre `party-identity` solo tiene `create`, `read`, `update`; le falta `delete`; `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `party-identity` solo tienen `read`; les falta `delete`; `inventario.test` — no tiene ningún permiso sobre `party-identity`

**Por qué se hace así**

- Ya no tiene hijos activos.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "id": "<SECTOR_X>",
  "classification_system": "EJEMPLO_INTERNO",
  "code": "X",
  "name": "Sector interno X",
  "parent_sector_id": null,
  "status": "INACTIVE",
  "version": 2
}
```

---

[← Paso anterior](01-recorrer-arbol-ciiu.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](03-consultar-pais.md)
