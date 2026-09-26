# Paso 02 de 04 — Registrar la empresa y su sucursal

Ejercicio 3 — Inactivar y reactivar una empresa · [← Paso anterior](01-consultar-organizacion.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](03-inactivar-empresa.md)

**Objetivo:** Crear la empresa y una sucursal activa.

**Necesita (de pasos anteriores):** `<ORG_EMPRESA>` — pasos [01](01-consultar-organizacion.md)

**Deja guardado para los siguientes pasos:** `<EMPRESA>`, `<SUCURSAL>`

---

## 1. Registrar la empresa

```http
POST /api/v1/companies
```

```json
{
  "organization_identity_id": "<ORG_EMPRESA>"
}
```

**Permisos que exige la URL (todos):** `perm:operational-context:companies:create` + `perm:operational-context:platform:administer`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`)
- ❌ **No pueden (responde `403`):** `supervisor.test` — sobre `operational-context` solo tiene `create`, `read`, `update`; le falta `administer`; `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `operational-context` solo tienen `read`; les falta `create`
- ℹ️ Para registrar o cambiar la organización o la ubicación, el token del usuario debe poder además **leer** en Party Identity y Geography: el servicio valida esas referencias con el mismo token. `administradores` y `supervisores` tienen esa lectura.
- ℹ️ Alcance de plataforma (Fase B, DS-05): registrar, inactivar y reactivar empresas y ver todas las empresas sin ser miembro. Solo lo concede `perm:all:all:all` (`administradores`); los comodines de lectura, creación o modificación **no** lo conceden.

**Por qué se hace así**

- Empresa mínima: solo la organización.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<EMPRESA>",
  "status": "ACTIVE",
  "version": 1
}
```

**Guardar:** `id` → `<EMPRESA>`

## 2. Registrar la sucursal

```http
POST /api/v1/companies/<EMPRESA>/branches
```

```json
{
  "code": "CEN-01",
  "name": "Oficina Centro (ficticia)"
}
```

**Permiso que exige la URL:** `perm:operational-context:branches:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `operational-context` solo tienen `read`; les falta `create`
- 🔒 Aislamiento por empresa (Fase B): además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa o `platform:administer`; si no, la URL responde `404`, igual que un `id` inexistente.

**Por qué se hace así**

- Sucursal sin ubicación: todos los campos de ubicación son opcionales.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<SUCURSAL>",
  "code": "CEN-01",
  "status": "ACTIVE",
  "company_status": "ACTIVE"
}
```

**Guardar:** `id` → `<SUCURSAL>`

---

[← Paso anterior](01-consultar-organizacion.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](03-inactivar-empresa.md)
