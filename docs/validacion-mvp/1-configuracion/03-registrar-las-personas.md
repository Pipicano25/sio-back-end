# Paso 03 de 08 — Registrar las personas

Ejercicio 1 — Configuración de la empresa: organizaciones, personas, empresas, sucursales y usuarios operativos · [Orden del ejercicio](ORDEN.md)

---

## 1. Registrar la persona cliente

Paso `C-02.cliente` · usuario **`admin.test`** · ítems de la FASE 10: 5

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

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)

**Por qué se hace así**

- Cada usuario operativo y el cliente persona se vinculan a una persona de Party Identity.

**Respuesta esperada:** `201`

**Guardar:** `id` → `<PERSONA_CLIENTE>`

**Auditoría que deja:** `CREATE_PERSON_IDENTITY` (party-identity)

## 2. Registrar la persona admin

Paso `C-02.admin` · usuario **`admin.test`** · ítems de la FASE 10: 3

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

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)

**Por qué se hace así**

- Cada usuario operativo y el cliente persona se vinculan a una persona de Party Identity.

**Respuesta esperada:** `201`

**Guardar:** `id` → `<PERSONA_ADMIN>`

**Auditoría que deja:** `CREATE_PERSON_IDENTITY` (party-identity)

## 3. Registrar la persona compras

Paso `C-02.compras` · usuario **`admin.test`** · ítems de la FASE 10: 3

```http
POST http://127.0.0.1:8101/api/v1/person-identities
```

```json
{
  "identification_country_id": "<PAIS_CO>",
  "identification_type": "CC",
  "identification_number": "<CC_COMPRAS>",
  "first_name": "COMPRASMVP<RUN_ID>",
  "last_name": "DATO FICTICIO DE VALIDACION",
  "birth_date": "1990-01-01"
}
```

**Permiso que exige la URL:** `perm:party-identity:person_identities:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)

**Por qué se hace así**

- Cada usuario operativo y el cliente persona se vinculan a una persona de Party Identity.

**Respuesta esperada:** `201`

**Guardar:** `id` → `<PERSONA_COMPRAS>`

**Auditoría que deja:** `CREATE_PERSON_IDENTITY` (party-identity)

## 4. Registrar la persona ventas

Paso `C-02.ventas` · usuario **`admin.test`** · ítems de la FASE 10: 3

```http
POST http://127.0.0.1:8101/api/v1/person-identities
```

```json
{
  "identification_country_id": "<PAIS_CO>",
  "identification_type": "CC",
  "identification_number": "<CC_VENTAS>",
  "first_name": "VENTASMVP<RUN_ID>",
  "last_name": "DATO FICTICIO DE VALIDACION",
  "birth_date": "1990-01-01"
}
```

**Permiso que exige la URL:** `perm:party-identity:person_identities:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)

**Por qué se hace así**

- Cada usuario operativo y el cliente persona se vinculan a una persona de Party Identity.

**Respuesta esperada:** `201`

**Guardar:** `id` → `<PERSONA_VENTAS>`

**Auditoría que deja:** `CREATE_PERSON_IDENTITY` (party-identity)

## 5. Registrar la persona supervisor

Paso `C-02.supervisor` · usuario **`admin.test`** · ítems de la FASE 10: 3

```http
POST http://127.0.0.1:8101/api/v1/person-identities
```

```json
{
  "identification_country_id": "<PAIS_CO>",
  "identification_type": "CC",
  "identification_number": "<CC_SUPERVISOR>",
  "first_name": "SUPERVISORMVP<RUN_ID>",
  "last_name": "DATO FICTICIO DE VALIDACION",
  "birth_date": "1990-01-01"
}
```

**Permiso que exige la URL:** `perm:party-identity:person_identities:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)

**Por qué se hace así**

- Cada usuario operativo y el cliente persona se vinculan a una persona de Party Identity.

**Respuesta esperada:** `201`

**Guardar:** `id` → `<PERSONA_SUPERVISOR>`

**Auditoría que deja:** `CREATE_PERSON_IDENTITY` (party-identity)

## 6. Registrar la persona consulta

Paso `C-02.consulta` · usuario **`admin.test`** · ítems de la FASE 10: 3

```http
POST http://127.0.0.1:8101/api/v1/person-identities
```

```json
{
  "identification_country_id": "<PAIS_CO>",
  "identification_type": "CC",
  "identification_number": "<CC_CONSULTA>",
  "first_name": "CONSULTAMVP<RUN_ID>",
  "last_name": "DATO FICTICIO DE VALIDACION",
  "birth_date": "1990-01-01"
}
```

**Permiso que exige la URL:** `perm:party-identity:person_identities:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)

**Por qué se hace así**

- Cada usuario operativo y el cliente persona se vinculan a una persona de Party Identity.

**Respuesta esperada:** `201`

**Guardar:** `id` → `<PERSONA_CONSULTA>`

**Auditoría que deja:** `CREATE_PERSON_IDENTITY` (party-identity)

## 7. Registrar la persona reportes

Paso `C-02.reportes` · usuario **`admin.test`** · ítems de la FASE 10: 3

```http
POST http://127.0.0.1:8101/api/v1/person-identities
```

```json
{
  "identification_country_id": "<PAIS_CO>",
  "identification_type": "CC",
  "identification_number": "<CC_REPORTES>",
  "first_name": "REPORTESMVP<RUN_ID>",
  "last_name": "DATO FICTICIO DE VALIDACION",
  "birth_date": "1990-01-01"
}
```

**Permiso que exige la URL:** `perm:party-identity:person_identities:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)

**Por qué se hace así**

- Cada usuario operativo y el cliente persona se vinculan a una persona de Party Identity.

**Respuesta esperada:** `201`

**Guardar:** `id` → `<PERSONA_REPORTES>`

**Auditoría que deja:** `CREATE_PERSON_IDENTITY` (party-identity)

## 8. Registrar la persona inventario

Paso `C-02.inventario` · usuario **`admin.test`** · ítems de la FASE 10: 3

```http
POST http://127.0.0.1:8101/api/v1/person-identities
```

```json
{
  "identification_country_id": "<PAIS_CO>",
  "identification_type": "CC",
  "identification_number": "<CC_INVENTARIO>",
  "first_name": "INVENTARIOMVP<RUN_ID>",
  "last_name": "DATO FICTICIO DE VALIDACION",
  "birth_date": "1990-01-01"
}
```

**Permiso que exige la URL:** `perm:party-identity:person_identities:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)

**Por qué se hace así**

- Cada usuario operativo y el cliente persona se vinculan a una persona de Party Identity.

**Respuesta esperada:** `201`

**Guardar:** `id` → `<PERSONA_INVENTARIO>`

**Auditoría que deja:** `CREATE_PERSON_IDENTITY` (party-identity)
