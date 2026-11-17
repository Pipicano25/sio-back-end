# Paso 02 de 05 — Registrar la organización

Ejercicio 4 — Perfil de contacto de una organización: versiones, no-op y cierre · [← Paso anterior](01-consultar-referencias.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](03-registrar-perfil.md)

**Objetivo:** Crear el proveedor (identidad global).

**Necesita (de pasos anteriores):** `<PAIS_CO>` — pasos [01](01-consultar-referencias.md)

**Deja guardado para los siguientes pasos:** `<ORG_PROVEEDOR>`

---

## 1. Registrar la organización

```http
POST /api/v1/organization-identities
```

```json
{
  "country_id": "<PAIS_CO>",
  "identification_type": "NIT",
  "identification_number": "900000004-4",
  "legal_name": "DISTRIBUIDORA CONTACTO FICTICIA S.A.S."
}
```

**Permiso que exige la URL:** `perm:party-identity:organization_identities:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:party-identity:all:create`), `compras.test` (por `perm:party-identity:organization_identities:create`), `ventas.test` (por `perm:party-identity:organization_identities:create`), `inventario.test` (por `perm:party-identity:organization_identities:create`)

**Por qué se hace así**

- Es la identidad global a la que pertenece el perfil de contacto.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<ORG_PROVEEDOR>",
  "legal_name": "DISTRIBUIDORA CONTACTO FICTICIA S.A.S.",
  "status": "ACTIVE",
  "version": 1
}
```

**Guardar:** `id` → `<ORG_PROVEEDOR>`

---

[← Paso anterior](01-consultar-referencias.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](03-registrar-perfil.md)
