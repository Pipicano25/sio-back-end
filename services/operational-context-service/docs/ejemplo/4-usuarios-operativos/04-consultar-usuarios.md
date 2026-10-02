# Paso 04 de 05 — Consultar los usuarios de la empresa A

Ejercicio 4 — Usuarios operativos de una empresa · [← Paso anterior](03-registrar-usuarios.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](05-misma-persona-otra-empresa.md)

**Objetivo:** Listar las membresías y consultar una por su `id`.

**Necesita (de pasos anteriores):** `<EMPRESA_A>`, `<USR_SUPERVISORA>` — pasos [02](02-registrar-empresas.md), [03](03-registrar-usuarios.md)

---

## 1. Listar los usuarios activos de la empresa A

```http
GET /api/v1/companies/<EMPRESA_A>/application-users
```

**Permiso que exige la URL:** `perm:operational-context:application_users:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:operational-context:all:read`), `ventas.test` (por `perm:operational-context:all:read`), `inventario.test` (por `perm:operational-context:all:read`), `reportes.test` (por `perm:operational-context:application_users:read`), `consulta.test` (por `perm:operational-context:application_users:read`)
- 🔒 Aislamiento por empresa (Fase B): además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa o `platform:administer`; si no, la URL responde `404`, igual que un `id` inexistente.

**Por qué se hace así**

- Solo los miembros de la empresa A (o el administrador de plataforma) la ven: `supervisor.test` y `compras.test` responden `200`; los demás, `404`.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "keycloak_user_id": "supervisor.test",
      "display_name": "Supervisora (ficticia)"
    },
    {
      "keycloak_user_id": "compras.test",
      "display_name": "Comprador (ficticio)"
    }
  ],
  "total_records": 2
}
```

## 2. Consultar la supervisora por su `id`

```http
GET /api/v1/application-users/<USR_SUPERVISORA>
```

**Permiso que exige la URL:** `perm:operational-context:application_users:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:operational-context:all:read`), `ventas.test` (por `perm:operational-context:all:read`), `inventario.test` (por `perm:operational-context:all:read`), `reportes.test` (por `perm:operational-context:application_users:read`), `consulta.test` (por `perm:operational-context:application_users:read`)
- 🔒 Aislamiento por empresa (Fase B): además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa o `platform:administer`; si no, la URL responde `404`, igual que un `id` inexistente.

**Por qué se hace así**

- Es la consulta que usan los demás servicios para el usuario operativo de un documento.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "id": "<USR_SUPERVISORA>",
  "company_id": "<EMPRESA_A>",
  "keycloak_user_id": "supervisor.test",
  "person_identity_id": "<PERSONA_SUPERVISORA>",
  "display_name": "Supervisora (ficticia)",
  "status": "ACTIVE",
  "version": 1
}
```

---

[← Paso anterior](03-registrar-usuarios.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](05-misma-persona-otra-empresa.md)
