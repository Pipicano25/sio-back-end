# Paso 02 de 08 — Registrar las organizaciones

Ejercicio 1 — Configuración de la empresa: organizaciones, personas, empresas, sucursales y usuarios operativos · [Orden del ejercicio](ORDEN.md)

---

## 1. Registrar la organización empresa a

Paso `C-01.empresa_a` · usuario **`admin.test`** · ítems de la FASE 10: 1

```http
POST http://127.0.0.1:8101/api/v1/organization-identities
```

```json
{
  "country_id": "<PAIS_CO>",
  "identification_type": "NIT",
  "identification_number": "<NIT_EMPRESA_A>",
  "legal_name": "EMPRESA A SIO MVP <RUN_ID> (DATO FICTICIO)"
}
```

**Permiso que exige la URL:** `perm:party-identity:organization_identities:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)

**Por qué se hace así**

- La razón social y el NIT pertenecen a Party Identity; la empresa y el proveedor solo guardan el id.

**Respuesta esperada:** `201`

**Guardar:** `id` → `<ORG_EMPRESA_A>`

**Auditoría que deja:** `CREATE_ORGANIZATION_IDENTITY` (party-identity)

## 2. Registrar la organización empresa b

Paso `C-01.empresa_b` · usuario **`admin.test`** · ítems de la FASE 10: 1

```http
POST http://127.0.0.1:8101/api/v1/organization-identities
```

```json
{
  "country_id": "<PAIS_CO>",
  "identification_type": "NIT",
  "identification_number": "<NIT_EMPRESA_B>",
  "legal_name": "EMPRESA B SIO MVP <RUN_ID> (DATO FICTICIO)"
}
```

**Permiso que exige la URL:** `perm:party-identity:organization_identities:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)

**Por qué se hace así**

- La razón social y el NIT pertenecen a Party Identity; la empresa y el proveedor solo guardan el id.

**Respuesta esperada:** `201`

**Guardar:** `id` → `<ORG_EMPRESA_B>`

**Auditoría que deja:** `CREATE_ORGANIZATION_IDENTITY` (party-identity)

## 3. Registrar la organización proveedor

Paso `C-01.proveedor` · usuario **`admin.test`** · ítems de la FASE 10: 1, 4

```http
POST http://127.0.0.1:8101/api/v1/organization-identities
```

```json
{
  "country_id": "<PAIS_CO>",
  "identification_type": "NIT",
  "identification_number": "<NIT_PROVEEDOR>",
  "legal_name": "PROVEEDOR SIO MVP <RUN_ID> (DATO FICTICIO)"
}
```

**Permiso que exige la URL:** `perm:party-identity:organization_identities:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)

**Por qué se hace así**

- La razón social y el NIT pertenecen a Party Identity; la empresa y el proveedor solo guardan el id.

**Respuesta esperada:** `201`

**Guardar:** `id` → `<ORG_PROVEEDOR>`

**Auditoría que deja:** `CREATE_ORGANIZATION_IDENTITY` (party-identity)
