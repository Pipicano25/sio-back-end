# Paso 07 de 08 — Asignar sucursales

Ejercicio 1 — Configuración de la empresa: organizaciones, personas, empresas, sucursales y usuarios operativos · [Orden del ejercicio](ORDEN.md)

---

## 1. Asignar a admin.test la sucursal A1

Paso `C-06.admin` · usuario **`admin.test`** · ítems de la FASE 10: 3

```http
POST http://127.0.0.1:8104/api/v1/application-users/<USUARIO_ADMIN>/user-branches
```

```json
{
  "branch_id": "<SUCURSAL_A1>"
}
```

**Permiso que exige la URL:** `perm:operational-context:user_branches:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)

**Respuesta esperada:** `201`

**Guardar:** `id` → `<ASIGNACION_ADMIN>`

**Auditoría que deja:** `ASSIGN_USER_BRANCH` (operational-context)

## 2. Asignar a compras.test la sucursal A1

Paso `C-06.compras` · usuario **`admin.test`** · ítems de la FASE 10: 3

```http
POST http://127.0.0.1:8104/api/v1/application-users/<USUARIO_COMPRAS>/user-branches
```

```json
{
  "branch_id": "<SUCURSAL_A1>"
}
```

**Permiso que exige la URL:** `perm:operational-context:user_branches:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)

**Respuesta esperada:** `201`

**Guardar:** `id` → `<ASIGNACION_COMPRAS>`

**Auditoría que deja:** `ASSIGN_USER_BRANCH` (operational-context)

## 3. Asignar a ventas.test la sucursal A1

Paso `C-06.ventas` · usuario **`admin.test`** · ítems de la FASE 10: 3

```http
POST http://127.0.0.1:8104/api/v1/application-users/<USUARIO_VENTAS>/user-branches
```

```json
{
  "branch_id": "<SUCURSAL_A1>"
}
```

**Permiso que exige la URL:** `perm:operational-context:user_branches:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)

**Respuesta esperada:** `201`

**Guardar:** `id` → `<ASIGNACION_VENTAS>`

**Auditoría que deja:** `ASSIGN_USER_BRANCH` (operational-context)

## 4. Asignar a supervisor.test la sucursal A1

Paso `C-06.supervisor` · usuario **`admin.test`** · ítems de la FASE 10: 3

```http
POST http://127.0.0.1:8104/api/v1/application-users/<USUARIO_SUPERVISOR>/user-branches
```

```json
{
  "branch_id": "<SUCURSAL_A1>"
}
```

**Permiso que exige la URL:** `perm:operational-context:user_branches:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)

**Respuesta esperada:** `201`

**Guardar:** `id` → `<ASIGNACION_SUPERVISOR>`

**Auditoría que deja:** `ASSIGN_USER_BRANCH` (operational-context)

## 5. Asignar a inventario.test la sucursal B1

Paso `C-06.inventario` · usuario **`admin.test`** · ítems de la FASE 10: 3

```http
POST http://127.0.0.1:8104/api/v1/application-users/<USUARIO_INVENTARIO>/user-branches
```

```json
{
  "branch_id": "<SUCURSAL_B1>"
}
```

**Permiso que exige la URL:** `perm:operational-context:user_branches:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)

**Respuesta esperada:** `201`

**Guardar:** `id` → `<ASIGNACION_INVENTARIO>`

**Auditoría que deja:** `ASSIGN_USER_BRANCH` (operational-context)
