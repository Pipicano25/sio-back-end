# Paso 02 de 04 — Seleccionar los proveedores

Ejercicio 3 — Proveedores, bloqueo y desbloqueo · [← Paso anterior](01-consultar-organizaciones.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](03-bloquear.md)

**Objetivo:** Registrar dos proveedores, uno de ellos también cliente.

**Necesita (de pasos anteriores):** `<EMPRESA>`, `<ORG_PROVEEDOR>`, `<ORG_PROVEEDOR_2>` — pasos [01](01-consultar-organizaciones.md)

**Deja guardado para los siguientes pasos:** `<PROVEEDOR>`, `<PROVEEDOR_2>`

---

## 1. Seleccionar el laboratorio como proveedor

```http
POST /api/v1/companies/<EMPRESA>/company-suppliers
```

```json
{
  "organization_identity_id": "<ORG_PROVEEDOR>",
  "internal_code": "PRV-0001",
  "display_name": "Laboratorio (ficticio)"
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_suppliers:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `company_suppliers` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `company_suppliers` de `commercial-relationship`
- ℹ️ Igual que los clientes: el token debe poder leer organizaciones y personas de contacto en Party Identity y la empresa en Operational Context.
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- El servicio comprueba que la organización no sea la de la empresa y que esté `ACTIVE` en Party Identity.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<PROVEEDOR>",
  "organization_identity_id": "<ORG_PROVEEDOR>",
  "internal_code": "PRV-0001",
  "display_name": "Laboratorio (ficticio)",
  "status": "ACTIVE",
  "block_reason": null,
  "version": 1
}
```

**Guardar:** `id` → `<PROVEEDOR>`

## 2. Registrar la importadora como cliente

```http
POST /api/v1/companies/<EMPRESA>/company-customers
```

```json
{
  "customer_kind": "ORGANIZATION",
  "organization_identity_id": "<ORG_PROVEEDOR_2>",
  "internal_code": "CLI-0001",
  "display_name": "Importadora (ficticia)"
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_customers:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `company_customers` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `company_customers` de `commercial-relationship`
- ℹ️ Para incorporar clientes el token del usuario debe poder además **leer** en Party Identity (personas, organizaciones y personas de contacto) y, para organizaciones, `perm:operational-context:companies:read` (comprobación de la propia empresa). `administradores` y `supervisores` tienen esa lectura.
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- Primero como cliente, para mostrar que también puede ser proveedor.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<id generado>",
  "customer_kind": "ORGANIZATION",
  "internal_code": "CLI-0001"
}
```

## 3. Seleccionar la importadora también como proveedor

```http
POST /api/v1/companies/<EMPRESA>/company-suppliers
```

```json
{
  "organization_identity_id": "<ORG_PROVEEDOR_2>",
  "internal_code": "PRV-0002",
  "display_name": "Importadora (ficticia)"
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_suppliers:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `company_suppliers` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `company_suppliers` de `commercial-relationship`
- ℹ️ Igual que los clientes: el token debe poder leer organizaciones y personas de contacto en Party Identity y la empresa en Operational Context.
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- Cliente y proveedor son relaciones independientes.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<PROVEEDOR_2>",
  "internal_code": "PRV-0002",
  "status": "ACTIVE"
}
```

**Guardar:** `id` → `<PROVEEDOR_2>`

## 4. Seleccionar otra vez el laboratorio (rechazado)

```http
POST /api/v1/companies/<EMPRESA>/company-suppliers
```

```json
{
  "organization_identity_id": "<ORG_PROVEEDOR>",
  "internal_code": "PRV-0099",
  "display_name": "Duplicado"
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_suppliers:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `company_suppliers` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `company_suppliers` de `commercial-relationship`
- ℹ️ Igual que los clientes: el token debe poder leer organizaciones y personas de contacto en Party Identity y la empresa en Operational Context.
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- Una empresa selecciona cada organización una sola vez: `409 DUPLICATE_SUPPLIER`.

**Respuesta esperada (error) — `409 Conflict`** (abreviada)

```json
{
  "status": 409,
  "code": "COMMERCIAL_RELATIONSHIP.DUPLICATE_SUPPLIER",
  "detail": "La organización ya es proveedor de la empresa; si está inactivo, reactívelo.",
  "errors": [
    {
      "field": "organization_identity_id",
      "message": "La organización ya es proveedor de la empresa; si está inactivo, reactívelo.",
      "code": "DUPLICATE_SUPPLIER"
    }
  ]
}
```

---

[← Paso anterior](01-consultar-organizaciones.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](03-bloquear.md)
