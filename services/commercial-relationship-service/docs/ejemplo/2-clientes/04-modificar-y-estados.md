# Paso 04 de 04 — Modificar, inactivar y reactivar

Ejercicio 2 — Clientes persona y organización · [← Paso anterior](03-cliente-organizacion.md) · [Orden del ejercicio](ORDEN.md)

**Objetivo:** Cambiar el nombre visible y el ciclo de vida del cliente.

**Necesita (de pasos anteriores):** `<CLIENTE_ORG>`, `<CLIENTE_PERSONA>`, `<EMPRESA>` — pasos [01](01-consultar-identidades.md), [02](02-cliente-persona.md), [03](03-cliente-organizacion.md)

---

## 1. Cambiar el nombre visible y quitar el contacto

```http
PUT /api/v1/company-customers/<CLIENTE_ORG>
```

```json
{
  "internal_code": "CLI-0100",
  "display_name": "Minimarket Centro (ficticio)",
  "preferred_contact_person_id": null,
  "version": 1
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_customers:update`

- ✅ **Pueden:** `admin.sio` (por `perm:all:all:all`), `admin.dao` (por `perm:commercial-relationship:all:update`)
- ❌ **No pueden (responde `403`):** `operario.dao` — sobre `company_customers` solo tiene `create`, `read`; le falta `update`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.sio`** (DS-03).

**Por qué se hace así**

- El `PUT` cambia código interno, nombre visible y contacto; tipo e identidad son inmutables.
- Quitar el contacto no consulta Party Identity.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "id": "<CLIENTE_ORG>",
  "display_name": "Minimarket Centro (ficticio)",
  "preferred_contact_person_id": null,
  "version": 2
}
```

## 2. Inactivar el cliente persona

```http
POST /api/v1/company-customers/<CLIENTE_PERSONA>/deactivate
```

```json
{
  "version": 1
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_customers:delete`

- ✅ **Pueden:** `admin.sio` (por `perm:all:all:all`), `admin.dao` (por `perm:commercial-relationship:all:delete`)
- ❌ **No pueden (responde `403`):** `operario.dao` — sobre `company_customers` solo tiene `create`, `read`; le falta `delete`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.sio`** (DS-03).

**Por qué se hace así**

- Inactivar exige `delete`; no borra nada.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "id": "<CLIENTE_PERSONA>",
  "status": "INACTIVE",
  "version": 2
}
```

## 3. Reactivar el cliente persona

```http
POST /api/v1/company-customers/<CLIENTE_PERSONA>/reactivate
```

```json
{
  "version": 2
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_customers:update`

- ✅ **Pueden:** `admin.sio` (por `perm:all:all:all`), `admin.dao` (por `perm:commercial-relationship:all:update`)
- ❌ **No pueden (responde `403`):** `operario.dao` — sobre `company_customers` solo tiene `create`, `read`; le falta `update`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.sio`** (DS-03).

**Por qué se hace así**

- Reactivar vuelve a validar que la persona siga `ACTIVE` en Party Identity.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "id": "<CLIENTE_PERSONA>",
  "status": "ACTIVE",
  "version": 3
}
```

## 4. Listar los clientes organización

```http
GET /api/v1/companies/<EMPRESA>/company-customers?customer_kind=ORGANIZATION
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_customers:read`

- ✅ **Pueden:** `admin.sio` (por `perm:all:all:all`), `admin.dao` (por `perm:commercial-relationship:all:read`), `operario.dao` (por `perm:commercial-relationship:company_customers:read`)
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.sio`** (DS-03).

**Por qué se hace así**

- Filtros por tipo, identidad, estado y búsqueda en código y nombre.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "internal_code": "CLI-0100",
      "display_name": "Minimarket Centro (ficticio)"
    }
  ],
  "total_records": 1
}
```

---

[← Paso anterior](03-cliente-organizacion.md) · [Orden del ejercicio](ORDEN.md)
