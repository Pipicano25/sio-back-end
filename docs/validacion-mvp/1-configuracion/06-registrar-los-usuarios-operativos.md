# Paso 06 de 08 — Registrar los usuarios operativos

Ejercicio 1 — Configuración de la empresa: organizaciones, personas, empresas, sucursales y usuarios operativos · [Orden del ejercicio](ORDEN.md)

---

## 1. Registrar a admin.sio como usuario operativo de la empresa A

Paso `C-05.admin` · usuario **`admin.sio`** · ítems de la FASE 10: 3

```http
POST http://127.0.0.1:8104/api/v1/companies/<EMPRESA_A>/application-users
```

```json
{
  "username": "admin.sio",
  "person_identity_id": "<PERSONA_ADMIN>",
  "display_name": "admin.sio MVP <RUN_ID> (dato ficticio)"
}
```

**Permiso que exige la URL:** `perm:operational-context:application_users:create`

- ✅ **Pueden:** `admin.sio` (por `perm:all:all:all`), `admin.dao` (por `perm:operational-context:all:create`)

**Por qué se hace así**

- "Crear usuario" registra el usuario operativo de una cuenta existente de Keycloak (C-01 de la Spec).

**Respuesta esperada:** `201`

**Guardar:** `id` → `<USUARIO_ADMIN>`

**Auditoría que deja:** `CREATE_APPLICATION_USER` (operational-context)

## 2. Registrar a operario.dao como usuario operativo de la empresa A

Paso `C-05.operario` · usuario **`admin.sio`** · ítems de la FASE 10: 3

```http
POST http://127.0.0.1:8104/api/v1/companies/<EMPRESA_A>/application-users
```

```json
{
  "username": "operario.dao",
  "person_identity_id": "<PERSONA_OPERARIO>",
  "display_name": "operario.dao MVP <RUN_ID> (dato ficticio)"
}
```

**Permiso que exige la URL:** `perm:operational-context:application_users:create`

- ✅ **Pueden:** `admin.sio` (por `perm:all:all:all`), `admin.dao` (por `perm:operational-context:all:create`)

**Por qué se hace así**

- "Crear usuario" registra el usuario operativo de una cuenta existente de Keycloak (C-01 de la Spec).

**Respuesta esperada:** `201`

**Guardar:** `id` → `<USUARIO_OPERARIO>`

**Auditoría que deja:** `CREATE_APPLICATION_USER` (operational-context)

## 3. Registrar a admin.dao como usuario operativo de la empresa B

Paso `C-05.admin_dao` · usuario **`admin.sio`** · ítems de la FASE 10: 3

```http
POST http://127.0.0.1:8104/api/v1/companies/<EMPRESA_B>/application-users
```

```json
{
  "username": "admin.dao",
  "person_identity_id": "<PERSONA_ADMIN_DAO>",
  "display_name": "admin.dao MVP <RUN_ID> (dato ficticio)"
}
```

**Permiso que exige la URL:** `perm:operational-context:application_users:create`

- ✅ **Pueden:** `admin.sio` (por `perm:all:all:all`), `admin.dao` (por `perm:operational-context:all:create`)

**Por qué se hace así**

- "Crear usuario" registra el usuario operativo de una cuenta existente de Keycloak (C-01 de la Spec).

**Respuesta esperada:** `201`

**Guardar:** `id` → `<USUARIO_ADMIN_DAO>`

**Auditoría que deja:** `CREATE_APPLICATION_USER` (operational-context)
