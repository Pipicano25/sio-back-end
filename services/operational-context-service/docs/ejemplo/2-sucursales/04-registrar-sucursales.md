# Paso 04 de 05 — Registrar las sucursales

Ejercicio 2 — Sucursales de una empresa · [← Paso anterior](03-registrar-empresa.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](05-consultar-y-cambiar-codigo.md)

**Objetivo:** Crear dos sucursales y comprobar los rechazos.

**Necesita (de pasos anteriores):** `<EMPRESA>`, `<PAIS_CO>`, `<DIV_ANT>`, `<CIU_MED>`, `<DIV_CUN>`, `<CIU_BOG>` — pasos [02](02-consultar-ubicacion.md), [03](03-registrar-empresa.md)

**Deja guardado para los siguientes pasos:** `<SUC_MED>`, `<SUC_BOG>`

---

## 1. Registrar la sucursal de Medellín sin zona horaria propia

```http
POST /api/v1/companies/<EMPRESA>/branches
```

```json
{
  "code": " med-01 ",
  "name": "Tienda El Poblado (ficticia)",
  "country_id": "<PAIS_CO>",
  "administrative_division_id": "<DIV_ANT>",
  "city_id": "<CIU_MED>"
}
```

**Permiso que exige la URL:** `perm:operational-context:branches:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `operational-context` solo tienen `read`; les falta `create`
- 🔒 Aislamiento por empresa (Fase B): además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa o `platform:administer`; si no, la URL responde `404`, igual que un `id` inexistente.

**Por qué se hace así**

- El código ` med-01 ` se normaliza a `MED-01`.
- Sin `timezone`, la sucursal usa la de la empresa (`effective_timezone`).

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<SUC_MED>",
  "company_id": "<EMPRESA>",
  "company_status": "ACTIVE",
  "code": "MED-01",
  "name": "Tienda El Poblado (ficticia)",
  "city_id": "<CIU_MED>",
  "timezone": null,
  "effective_timezone": "America/Bogota",
  "status": "ACTIVE",
  "version": 1
}
```

**Guardar:** `id` → `<SUC_MED>`

## 2. Registrar la bodega de Bogotá con zona horaria propia

```http
POST /api/v1/companies/<EMPRESA>/branches
```

```json
{
  "code": "BOG-01",
  "name": "Bodega Norte (ficticia)",
  "country_id": "<PAIS_CO>",
  "administrative_division_id": "<DIV_CUN>",
  "city_id": "<CIU_BOG>",
  "timezone": "America/Bogota"
}
```

**Permiso que exige la URL:** `perm:operational-context:branches:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `operational-context` solo tienen `read`; les falta `create`
- 🔒 Aislamiento por empresa (Fase B): además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa o `platform:administer`; si no, la URL responde `404`, igual que un `id` inexistente.

**Por qué se hace así**

- Con `timezone` propia, esa prevalece sobre la de la empresa.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<SUC_BOG>",
  "company_id": "<EMPRESA>",
  "company_status": "ACTIVE",
  "code": "BOG-01",
  "name": "Bodega Norte (ficticia)",
  "city_id": "<CIU_BOG>",
  "timezone": "America/Bogota",
  "effective_timezone": "America/Bogota",
  "status": "ACTIVE",
  "version": 1
}
```

**Guardar:** `id` → `<SUC_BOG>`

## 3. Intentar repetir el código MED-01 (rechazado)

```http
POST /api/v1/companies/<EMPRESA>/branches
```

```json
{
  "code": "MED-01",
  "name": "Otra tienda (ficticia)"
}
```

**Permiso que exige la URL:** `perm:operational-context:branches:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `operational-context` solo tienen `read`; les falta `create`
- 🔒 Aislamiento por empresa (Fase B): además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa o `platform:administer`; si no, la URL responde `404`, igual que un `id` inexistente.

**Por qué se hace así**

- El código ya existe en la empresa: `409 DUPLICATE_BRANCH_CODE`.

**Respuesta esperada (error) — `409 Conflict`** (abreviada)

```json
{
  "status": 409,
  "code": "OPERATIONAL_CONTEXT.DUPLICATE_BRANCH_CODE",
  "detail": "Ya existe una sucursal con ese código en la empresa."
}
```

## 4. Intentar Medellín con el departamento de Cundinamarca (rechazado)

```http
POST /api/v1/companies/<EMPRESA>/branches
```

```json
{
  "code": "MED-02",
  "name": "Tienda El Poblado (ficticia)",
  "country_id": "<PAIS_CO>",
  "administrative_division_id": "<DIV_CUN>",
  "city_id": "<CIU_MED>"
}
```

**Permiso que exige la URL:** `perm:operational-context:branches:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `operational-context` solo tienen `read`; les falta `create`
- 🔒 Aislamiento por empresa (Fase B): además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa o `platform:administer`; si no, la URL responde `404`, igual que un `id` inexistente.

**Por qué se hace así**

- La ciudad no pertenece a la división enviada: `422 GEOGRAPHY_INCOHERENT` en `city_id`.

**Respuesta esperada (error) — `422 Unprocessable Content`** (abreviada)

```json
{
  "status": 422,
  "code": "OPERATIONAL_CONTEXT.GEOGRAPHY_INCOHERENT",
  "detail": "La ciudad no pertenece a la división administrativa enviada.",
  "errors": [
    {
      "field": "city_id",
      "message": "La ciudad no pertenece a la división administrativa enviada.",
      "code": "GEOGRAPHY_INCOHERENT"
    }
  ]
}
```

---

[← Paso anterior](03-registrar-empresa.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](05-consultar-y-cambiar-codigo.md)
