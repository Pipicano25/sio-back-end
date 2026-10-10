# Paso 06 de 08 — Registrar los usuarios operativos

Ejercicio 1 — Configuración de la empresa: organizaciones, personas, empresas, sucursales y usuarios operativos · [Orden del ejercicio](ORDEN.md)

---

## 1. Registrar a admin.test como usuario operativo de la empresa A

Paso `C-05.admin` · usuario **`admin.test`** · ítems de la FASE 10: 3

```http
POST http://127.0.0.1:8104/api/v1/companies/<EMPRESA_A>/application-users
```

```json
{
  "username": "admin.test",
  "person_identity_id": "<PERSONA_ADMIN>",
  "display_name": "admin.test MVP <RUN_ID> (dato ficticio)"
}
```

**Permiso que exige la URL:** `perm:operational-context:application_users:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)

**Por qué se hace así**

- "Crear usuario" registra el usuario operativo de una cuenta existente de Keycloak (C-01 de la Spec).

**Respuesta esperada:** `201`

**Guardar:** `id` → `<USUARIO_ADMIN>`

**Auditoría que deja:** `CREATE_APPLICATION_USER` (operational-context)

## 2. Registrar a compras.test como usuario operativo de la empresa A

Paso `C-05.compras` · usuario **`admin.test`** · ítems de la FASE 10: 3

```http
POST http://127.0.0.1:8104/api/v1/companies/<EMPRESA_A>/application-users
```

```json
{
  "username": "compras.test",
  "person_identity_id": "<PERSONA_COMPRAS>",
  "display_name": "compras.test MVP <RUN_ID> (dato ficticio)"
}
```

**Permiso que exige la URL:** `perm:operational-context:application_users:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)

**Por qué se hace así**

- "Crear usuario" registra el usuario operativo de una cuenta existente de Keycloak (C-01 de la Spec).

**Respuesta esperada:** `201`

**Guardar:** `id` → `<USUARIO_COMPRAS>`

**Auditoría que deja:** `CREATE_APPLICATION_USER` (operational-context)

## 3. Registrar a ventas.test como usuario operativo de la empresa A

Paso `C-05.ventas` · usuario **`admin.test`** · ítems de la FASE 10: 3

```http
POST http://127.0.0.1:8104/api/v1/companies/<EMPRESA_A>/application-users
```

```json
{
  "username": "ventas.test",
  "person_identity_id": "<PERSONA_VENTAS>",
  "display_name": "ventas.test MVP <RUN_ID> (dato ficticio)"
}
```

**Permiso que exige la URL:** `perm:operational-context:application_users:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)

**Por qué se hace así**

- "Crear usuario" registra el usuario operativo de una cuenta existente de Keycloak (C-01 de la Spec).

**Respuesta esperada:** `201`

**Guardar:** `id` → `<USUARIO_VENTAS>`

**Auditoría que deja:** `CREATE_APPLICATION_USER` (operational-context)

## 4. Registrar a supervisor.test como usuario operativo de la empresa A

Paso `C-05.supervisor` · usuario **`admin.test`** · ítems de la FASE 10: 3

```http
POST http://127.0.0.1:8104/api/v1/companies/<EMPRESA_A>/application-users
```

```json
{
  "username": "supervisor.test",
  "person_identity_id": "<PERSONA_SUPERVISOR>",
  "display_name": "supervisor.test MVP <RUN_ID> (dato ficticio)"
}
```

**Permiso que exige la URL:** `perm:operational-context:application_users:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)

**Por qué se hace así**

- "Crear usuario" registra el usuario operativo de una cuenta existente de Keycloak (C-01 de la Spec).

**Respuesta esperada:** `201`

**Guardar:** `id` → `<USUARIO_SUPERVISOR>`

**Auditoría que deja:** `CREATE_APPLICATION_USER` (operational-context)

## 5. Registrar a consulta.test como usuario operativo de la empresa A

Paso `C-05.consulta` · usuario **`admin.test`** · ítems de la FASE 10: 3

```http
POST http://127.0.0.1:8104/api/v1/companies/<EMPRESA_A>/application-users
```

```json
{
  "username": "consulta.test",
  "person_identity_id": "<PERSONA_CONSULTA>",
  "display_name": "consulta.test MVP <RUN_ID> (dato ficticio)"
}
```

**Permiso que exige la URL:** `perm:operational-context:application_users:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)

**Por qué se hace así**

- "Crear usuario" registra el usuario operativo de una cuenta existente de Keycloak (C-01 de la Spec).

**Respuesta esperada:** `201`

**Guardar:** `id` → `<USUARIO_CONSULTA>`

**Auditoría que deja:** `CREATE_APPLICATION_USER` (operational-context)

## 6. Registrar a reportes.test como usuario operativo de la empresa B

Paso `C-05.reportes` · usuario **`admin.test`** · ítems de la FASE 10: 3

```http
POST http://127.0.0.1:8104/api/v1/companies/<EMPRESA_B>/application-users
```

```json
{
  "username": "reportes.test",
  "person_identity_id": "<PERSONA_REPORTES>",
  "display_name": "reportes.test MVP <RUN_ID> (dato ficticio)"
}
```

**Permiso que exige la URL:** `perm:operational-context:application_users:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)

**Por qué se hace así**

- "Crear usuario" registra el usuario operativo de una cuenta existente de Keycloak (C-01 de la Spec).

**Respuesta esperada:** `201`

**Guardar:** `id` → `<USUARIO_REPORTES>`

**Auditoría que deja:** `CREATE_APPLICATION_USER` (operational-context)

## 7. Registrar a inventario.test como usuario operativo de la empresa B

Paso `C-05.inventario` · usuario **`admin.test`** · ítems de la FASE 10: 3

```http
POST http://127.0.0.1:8104/api/v1/companies/<EMPRESA_B>/application-users
```

```json
{
  "username": "inventario.test",
  "person_identity_id": "<PERSONA_INVENTARIO>",
  "display_name": "inventario.test MVP <RUN_ID> (dato ficticio)"
}
```

**Permiso que exige la URL:** `perm:operational-context:application_users:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)

**Por qué se hace así**

- "Crear usuario" registra el usuario operativo de una cuenta existente de Keycloak (C-01 de la Spec).

**Respuesta esperada:** `201`

**Guardar:** `id` → `<USUARIO_INVENTARIO>`

**Auditoría que deja:** `CREATE_APPLICATION_USER` (operational-context)
