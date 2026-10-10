# Paso 05 de 08 — Registrar las sucursales

Ejercicio 1 — Configuración de la empresa: organizaciones, personas, empresas, sucursales y usuarios operativos · [Orden del ejercicio](ORDEN.md)

---

## 1. Registrar la sucursal A1

Paso `C-04.a1` · usuario **`admin.test`** · ítems de la FASE 10: 2

```http
POST http://127.0.0.1:8104/api/v1/companies/<EMPRESA_A>/branches
```

```json
{
  "code": "A1<RUN_ID>",
  "name": "Sucursal A1 <RUN_ID> (dato ficticio)",
  "country_id": "<PAIS_CO>",
  "administrative_division_id": "<DEPARTAMENTO>",
  "city_id": "<CIUDAD>"
}
```

**Permiso que exige la URL:** `perm:operational-context:branches:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)

**Por qué se hace así**

- La zona horaria efectiva de la sucursal define la fecha de negocio de compras y ventas.

**Respuesta esperada:** `201`

**Guardar:** `id` → `<SUCURSAL_A1>`, `effective_timezone` → `<ZONA_A1>`

**Auditoría que deja:** `CREATE_BRANCH` (operational-context)

## 2. Registrar la sucursal B1

Paso `C-04.b1` · usuario **`admin.test`** · ítems de la FASE 10: 2

```http
POST http://127.0.0.1:8104/api/v1/companies/<EMPRESA_B>/branches
```

```json
{
  "code": "B1<RUN_ID>",
  "name": "Sucursal B1 <RUN_ID> (dato ficticio)",
  "country_id": "<PAIS_CO>",
  "administrative_division_id": "<DEPARTAMENTO>",
  "city_id": "<CIUDAD>"
}
```

**Permiso que exige la URL:** `perm:operational-context:branches:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)

**Por qué se hace así**

- La zona horaria efectiva de la sucursal define la fecha de negocio de compras y ventas.

**Respuesta esperada:** `201`

**Guardar:** `id` → `<SUCURSAL_B1>`, `effective_timezone` → `<ZONA_B1>`

**Auditoría que deja:** `CREATE_BRANCH` (operational-context)
