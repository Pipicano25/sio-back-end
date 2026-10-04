# Paso 02 de 04 — Incorporar un cliente persona

Ejercicio 2 — Clientes persona y organización · [← Paso anterior](01-consultar-identidades.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](03-cliente-organizacion.md)

**Objetivo:** Registrar a la persona como cliente.

**Necesita (de pasos anteriores):** `<EMPRESA>`, `<PERSONA>`, `<CONTACTO>` — pasos [01](01-consultar-identidades.md)

**Deja guardado para los siguientes pasos:** `<CLIENTE_PERSONA>`

---

## 1. Incorporar el cliente persona

```http
POST /api/v1/companies/<EMPRESA>/company-customers
```

```json
{
  "customer_kind": "PERSON",
  "person_identity_id": "<PERSONA>",
  "internal_code": "CLI-0001",
  "display_name": "Cliente persona (ficticio)"
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_customers:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `company_customers` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `company_customers` de `commercial-relationship`
- ℹ️ Para incorporar clientes el token del usuario debe poder además **leer** en Party Identity (personas, organizaciones y personas de contacto) y, para organizaciones, `perm:operational-context:companies:read` (comprobación de la propia empresa). `administradores` y `supervisores` tienen esa lectura.
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- El servicio valida en Party Identity, **con el token del usuario**, que la persona exista y esté `ACTIVE`; si el usuario no puede leer personas, responde `403 PARTY_IDENTITY_ACCESS_DENIED`.
- `display_name` es obligatorio: lo escribe el usuario (DS-14).

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<CLIENTE_PERSONA>",
  "customer_kind": "PERSON",
  "person_identity_id": "<PERSONA>",
  "organization_identity_id": null,
  "internal_code": "CLI-0001",
  "display_name": "Cliente persona (ficticio)",
  "preferred_contact_person_id": null,
  "status": "ACTIVE",
  "version": 1
}
```

**Guardar:** `id` → `<CLIENTE_PERSONA>`

## 2. Indicar un contacto preferido para una persona (rechazado)

```http
POST /api/v1/companies/<EMPRESA>/company-customers
```

```json
{
  "customer_kind": "PERSON",
  "person_identity_id": "<PERSONA>",
  "internal_code": "CLI-0002",
  "display_name": "Otro",
  "preferred_contact_person_id": "<CONTACTO>"
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_customers:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `company_customers` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `company_customers` de `commercial-relationship`
- ℹ️ Para incorporar clientes el token del usuario debe poder además **leer** en Party Identity (personas, organizaciones y personas de contacto) y, para organizaciones, `perm:operational-context:companies:read` (comprobación de la propia empresa). `administradores` y `supervisores` tienen esa lectura.
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- Solo los clientes `ORGANIZATION` admiten persona de contacto: `422 CONTACT_PERSON_NOT_ALLOWED`.

**Respuesta esperada (error) — `422 Unprocessable Content`** (abreviada)

```json
{
  "status": 422,
  "code": "COMMERCIAL_RELATIONSHIP.CONTACT_PERSON_NOT_ALLOWED",
  "detail": "Solo los clientes ORGANIZATION admiten persona de contacto preferida.",
  "errors": [
    {
      "field": "preferred_contact_person_id",
      "message": "Solo los clientes ORGANIZATION admiten persona de contacto preferida.",
      "code": "CONTACT_PERSON_NOT_ALLOWED"
    }
  ]
}
```

---

[← Paso anterior](01-consultar-identidades.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](03-cliente-organizacion.md)
