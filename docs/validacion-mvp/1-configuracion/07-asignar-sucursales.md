# Paso 07 de 08 — Asignar sucursales

Ejercicio 1 — Configuración de la empresa: organizaciones, personas, empresas, sucursales y usuarios operativos · [Orden del ejercicio](ORDEN.md)

---

## 1. Asignar a admin.sio la sucursal A1

Paso `C-06.admin` · usuario **`admin.sio`** · ítems de la FASE 10: 3

```http
POST http://127.0.0.1:8104/api/v1/application-users/<USUARIO_ADMIN>/user-branches
```

```json
{
  "branch_id": "<SUCURSAL_A1>"
}
```

**Permiso que exige la URL:** `perm:operational-context:user_branches:create`

- ✅ **Pueden:** `admin.sio` (por `perm:all:all:all`), `admin.dao` (por `perm:operational-context:all:create`)

**Respuesta esperada:** `201`

**Guardar:** `id` → `<ASIGNACION_ADMIN>`

**Auditoría que deja:** `ASSIGN_USER_BRANCH` (operational-context)

## 2. Asignar a operario.dao la sucursal A1

Paso `C-06.operario` · usuario **`admin.sio`** · ítems de la FASE 10: 3

```http
POST http://127.0.0.1:8104/api/v1/application-users/<USUARIO_OPERARIO>/user-branches
```

```json
{
  "branch_id": "<SUCURSAL_A1>"
}
```

**Permiso que exige la URL:** `perm:operational-context:user_branches:create`

- ✅ **Pueden:** `admin.sio` (por `perm:all:all:all`), `admin.dao` (por `perm:operational-context:all:create`)

**Respuesta esperada:** `201`

**Guardar:** `id` → `<ASIGNACION_OPERARIO>`

**Auditoría que deja:** `ASSIGN_USER_BRANCH` (operational-context)

## 3. Asignar a admin.dao la sucursal B1

Paso `C-06.admin_dao` · usuario **`admin.sio`** · ítems de la FASE 10: 3

```http
POST http://127.0.0.1:8104/api/v1/application-users/<USUARIO_ADMIN_DAO>/user-branches
```

```json
{
  "branch_id": "<SUCURSAL_B1>"
}
```

**Permiso que exige la URL:** `perm:operational-context:user_branches:create`

- ✅ **Pueden:** `admin.sio` (por `perm:all:all:all`), `admin.dao` (por `perm:operational-context:all:create`)

**Respuesta esperada:** `201`

**Guardar:** `id` → `<ASIGNACION_ADMIN_DAO>`

**Auditoría que deja:** `ASSIGN_USER_BRANCH` (operational-context)
