# Paso 03 de 04 — Incorporar un cliente organización

Ejercicio 2 — Clientes persona y organización · [← Paso anterior](02-cliente-persona.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](04-modificar-y-estados.md)

**Objetivo:** Registrar la organización con su contacto y ver los rechazos.

**Necesita (de pasos anteriores):** `<EMPRESA>`, `<ORG_CLIENTE>`, `<CONTACTO_OTRA>`, `<CONTACTO>`, `<ORG_EMPRESA>` — pasos [01](01-consultar-identidades.md)

**Deja guardado para los siguientes pasos:** `<CLIENTE_ORG>`

---

## 1. Indicar el contacto de otra organización (rechazado)

```http
POST /api/v1/companies/<EMPRESA>/company-customers
```

```json
{
  "customer_kind": "ORGANIZATION",
  "organization_identity_id": "<ORG_CLIENTE>",
  "internal_code": "CLI-0100",
  "display_name": "Minimarket (ficticio)",
  "preferred_contact_person_id": "<CONTACTO_OTRA>"
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_customers:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `company_customers` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `company_customers` de `commercial-relationship`
- ℹ️ Para incorporar clientes el token del usuario debe poder además **leer** en Party Identity (personas, organizaciones y personas de contacto) y, para organizaciones, `perm:operational-context:companies:read` (comprobación de la propia empresa). `administradores` y `supervisores` tienen esa lectura.
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- El contacto debe pertenecer a la **misma** organización: `422 CONTACT_PERSON_INVALID`.

**Respuesta esperada (error) — `422 Unprocessable Content`** (abreviada)

```json
{
  "status": 422,
  "code": "COMMERCIAL_RELATIONSHIP.CONTACT_PERSON_INVALID",
  "detail": "La persona de contacto no existe, está inactiva o no pertenece a la organización.",
  "errors": [
    {
      "field": "preferred_contact_person_id",
      "message": "La persona de contacto no existe, está inactiva o no pertenece a la organización.",
      "code": "CONTACT_PERSON_INVALID"
    }
  ]
}
```

## 2. Incorporar el cliente organización con su contacto

```http
POST /api/v1/companies/<EMPRESA>/company-customers
```

```json
{
  "customer_kind": "ORGANIZATION",
  "organization_identity_id": "<ORG_CLIENTE>",
  "internal_code": "CLI-0100",
  "display_name": "Minimarket (ficticio)",
  "preferred_contact_person_id": "<CONTACTO>"
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_customers:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `company_customers` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `company_customers` de `commercial-relationship`
- ℹ️ Para incorporar clientes el token del usuario debe poder además **leer** en Party Identity (personas, organizaciones y personas de contacto) y, para organizaciones, `perm:operational-context:companies:read` (comprobación de la propia empresa). `administradores` y `supervisores` tienen esa lectura.
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- Antes de Party Identity, el servicio consulta la empresa en Operational Context para comprobar que la organización no sea la de la propia empresa (DS-15).

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<CLIENTE_ORG>",
  "customer_kind": "ORGANIZATION",
  "person_identity_id": null,
  "organization_identity_id": "<ORG_CLIENTE>",
  "internal_code": "CLI-0100",
  "display_name": "Minimarket (ficticio)",
  "preferred_contact_person_id": "<CONTACTO>",
  "status": "ACTIVE",
  "version": 1
}
```

**Guardar:** `id` → `<CLIENTE_ORG>`

## 3. Incorporar la propia empresa como cliente (rechazado)

```http
POST /api/v1/companies/<EMPRESA>/company-customers
```

```json
{
  "customer_kind": "ORGANIZATION",
  "organization_identity_id": "<ORG_EMPRESA>",
  "internal_code": "CLI-YO",
  "display_name": "La propia empresa"
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_customers:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `company_customers` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `company_customers` de `commercial-relationship`
- ℹ️ Para incorporar clientes el token del usuario debe poder además **leer** en Party Identity (personas, organizaciones y personas de contacto) y, para organizaciones, `perm:operational-context:companies:read` (comprobación de la propia empresa). `administradores` y `supervisores` tienen esa lectura.
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- Una empresa nunca es cliente de sí misma: `422 SELF_RELATIONSHIP_NOT_ALLOWED`.

**Respuesta esperada (error) — `422 Unprocessable Content`** (abreviada)

```json
{
  "status": 422,
  "code": "COMMERCIAL_RELATIONSHIP.SELF_RELATIONSHIP_NOT_ALLOWED",
  "detail": "Una empresa no puede ser cliente ni proveedor de sí misma.",
  "errors": [
    {
      "field": "organization_identity_id",
      "message": "Una empresa no puede ser cliente ni proveedor de sí misma.",
      "code": "SELF_RELATIONSHIP_NOT_ALLOWED"
    }
  ]
}
```

---

[← Paso anterior](02-cliente-persona.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](04-modificar-y-estados.md)
