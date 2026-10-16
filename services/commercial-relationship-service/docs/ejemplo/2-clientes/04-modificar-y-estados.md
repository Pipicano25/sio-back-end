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

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `company_customers` solo tienen `read`; les falta `update`; `inventario.test` — no tiene ningún permiso sobre `company_customers` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

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

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`)
- ❌ **No pueden (responde `403`):** `supervisor.test` — sobre `company_customers` solo tiene `create`, `read`, `update`; le falta `delete`; `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `company_customers` solo tienen `read`; les falta `delete`; `inventario.test` — no tiene ningún permiso sobre `company_customers` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

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

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `company_customers` solo tienen `read`; les falta `update`; `inventario.test` — no tiene ningún permiso sobre `company_customers` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

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

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:commercial-relationship:company_customers:read`), `ventas.test` (por `perm:commercial-relationship:company_customers:read`), `reportes.test` (por `perm:commercial-relationship:company_customers:read`), `consulta.test` (por `perm:commercial-relationship:company_customers:read`)
- ❌ **No pueden (responde `403`):** `inventario.test` — no tiene ningún permiso sobre `company_customers` de `commercial-relationship`
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

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
