# Paso 03 de 08 — Registrar las personas

Ejercicio 1 — Configuración de la empresa: organizaciones, personas, empresas, sucursales y usuarios operativos · [Orden del ejercicio](ORDEN.md)

---

## 1. Registrar la persona cliente

Paso `C-02.cliente` · usuario **`admin.sio`** · ítems de la FASE 10: 5

```http
POST http://127.0.0.1:8101/api/v1/person-identities
```

```json
{
  "identification_country_id": "<PAIS_CO>",
  "identification_type": "CC",
  "identification_number": "<CC_CLIENTE>",
  "first_name": "CLIENTEMVP<RUN_ID>",
  "last_name": "DATO FICTICIO DE VALIDACION",
  "birth_date": "1990-01-01"
}
```

**Permiso que exige la URL:** `perm:party-identity:person_identities:create`

- ✅ **Pueden:** `admin.sio` (por `perm:all:all:all`), `admin.dao` (por `perm:party-identity:all:create`), `operario.dao` (por `perm:party-identity:person_identities:create`)

**Por qué se hace así**

- Cada usuario operativo y el cliente persona se vinculan a una persona de Party Identity.

**Respuesta esperada:** `201`

**Guardar:** `id` → `<PERSONA_CLIENTE>`

**Auditoría que deja:** `CREATE_PERSON_IDENTITY` (party-identity)

## 2. Registrar la persona admin

Paso `C-02.admin` · usuario **`admin.sio`** · ítems de la FASE 10: 3

```http
POST http://127.0.0.1:8101/api/v1/person-identities
```

```json
{
  "identification_country_id": "<PAIS_CO>",
  "identification_type": "CC",
  "identification_number": "<CC_ADMIN>",
  "first_name": "ADMINMVP<RUN_ID>",
  "last_name": "DATO FICTICIO DE VALIDACION",
  "birth_date": "1990-01-01"
}
```

**Permiso que exige la URL:** `perm:party-identity:person_identities:create`

- ✅ **Pueden:** `admin.sio` (por `perm:all:all:all`), `admin.dao` (por `perm:party-identity:all:create`), `operario.dao` (por `perm:party-identity:person_identities:create`)

**Por qué se hace así**

- Cada usuario operativo y el cliente persona se vinculan a una persona de Party Identity.

**Respuesta esperada:** `201`

**Guardar:** `id` → `<PERSONA_ADMIN>`

**Auditoría que deja:** `CREATE_PERSON_IDENTITY` (party-identity)

## 3. Registrar la persona operario

Paso `C-02.operario` · usuario **`admin.sio`** · ítems de la FASE 10: 3

```http
POST http://127.0.0.1:8101/api/v1/person-identities
```

```json
{
  "identification_country_id": "<PAIS_CO>",
  "identification_type": "CC",
  "identification_number": "<CC_OPERARIO>",
  "first_name": "OPERARIOMVP<RUN_ID>",
  "last_name": "DATO FICTICIO DE VALIDACION",
  "birth_date": "1990-01-01"
}
```

**Permiso que exige la URL:** `perm:party-identity:person_identities:create`

- ✅ **Pueden:** `admin.sio` (por `perm:all:all:all`), `admin.dao` (por `perm:party-identity:all:create`), `operario.dao` (por `perm:party-identity:person_identities:create`)

**Por qué se hace así**

- Cada usuario operativo y el cliente persona se vinculan a una persona de Party Identity.

**Respuesta esperada:** `201`

**Guardar:** `id` → `<PERSONA_OPERARIO>`

**Auditoría que deja:** `CREATE_PERSON_IDENTITY` (party-identity)

## 4. Registrar la persona admin_dao

Paso `C-02.admin_dao` · usuario **`admin.sio`** · ítems de la FASE 10: 3

```http
POST http://127.0.0.1:8101/api/v1/person-identities
```

```json
{
  "identification_country_id": "<PAIS_CO>",
  "identification_type": "CC",
  "identification_number": "<CC_ADMIN_DAO>",
  "first_name": "ADMIN_DAOMVP<RUN_ID>",
  "last_name": "DATO FICTICIO DE VALIDACION",
  "birth_date": "1990-01-01"
}
```

**Permiso que exige la URL:** `perm:party-identity:person_identities:create`

- ✅ **Pueden:** `admin.sio` (por `perm:all:all:all`), `admin.dao` (por `perm:party-identity:all:create`), `operario.dao` (por `perm:party-identity:person_identities:create`)

**Por qué se hace así**

- Cada usuario operativo y el cliente persona se vinculan a una persona de Party Identity.

**Respuesta esperada:** `201`

**Guardar:** `id` → `<PERSONA_ADMIN_DAO>`

**Auditoría que deja:** `CREATE_PERSON_IDENTITY` (party-identity)
