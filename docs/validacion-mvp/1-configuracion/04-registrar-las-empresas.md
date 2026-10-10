# Paso 04 de 08 — Registrar las empresas

Ejercicio 1 — Configuración de la empresa: organizaciones, personas, empresas, sucursales y usuarios operativos · [Orden del ejercicio](ORDEN.md)

---

## 1. Registrar la empresa A

Paso `C-03.a` · usuario **`admin.test`** · ítems de la FASE 10: 1

```http
POST http://127.0.0.1:8104/api/v1/companies
```

```json
{
  "organization_identity_id": "<ORG_EMPRESA_A>"
}
```

**Permiso que exige la URL:** `perm:operational-context:companies:create` + `perm:operational-context:platform:administer`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`)

**Por qué se hace así**

- La moneda por defecto de la empresa es COP; la empresa no guarda NIT ni razón social.

**Respuesta esperada:** `201` — `default_currency` = `COP`, `status` = `ACTIVE`

**Guardar:** `id` → `<EMPRESA_A>`

**Auditoría que deja:** `CREATE_COMPANY` (operational-context)

## 2. Registrar la empresa B

Paso `C-03.b` · usuario **`admin.test`** · ítems de la FASE 10: 1

```http
POST http://127.0.0.1:8104/api/v1/companies
```

```json
{
  "organization_identity_id": "<ORG_EMPRESA_B>"
}
```

**Permiso que exige la URL:** `perm:operational-context:companies:create` + `perm:operational-context:platform:administer`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`)

**Por qué se hace así**

- La moneda por defecto de la empresa es COP; la empresa no guarda NIT ni razón social.

**Respuesta esperada:** `201` — `default_currency` = `COP`, `status` = `ACTIVE`

**Guardar:** `id` → `<EMPRESA_B>`

**Auditoría que deja:** `CREATE_COMPANY` (operational-context)
