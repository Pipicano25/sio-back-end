# Paso 03 de 04 — Registrar la empresa

Ejercicio 1 — Empresa con su sede operativa principal · [← Paso anterior](02-consultar-ubicacion.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](04-consultar-y-modificar.md)

**Objetivo:** Crear la empresa y comprobar el rechazo por organización inexistente.

**Necesita (de pasos anteriores):** `<ORG_EMPRESA>`, `<PAIS_CO>`, `<DIV_ANT>`, `<CIU_MED>` — pasos [01](01-consultar-organizacion.md), [02](02-consultar-ubicacion.md)

**Deja guardado para los siguientes pasos:** `<EMPRESA>`

---

## 1. Registrar la empresa con su sede operativa principal

```http
POST /api/v1/companies
```

```json
{
  "organization_identity_id": "<ORG_EMPRESA>",
  "email": "contacto@comercializadora-ficticia.co",
  "phone": "+57 604 000 0001",
  "address_line": "Carrera Ficticia 43A # 1-50",
  "country_id": "<PAIS_CO>",
  "administrative_division_id": "<DIV_ANT>",
  "city_id": "<CIU_MED>",
  "postal_code": "050021",
  "latitude": "6.208000",
  "longitude": "-75.567000"
}
```

**Permisos que exige la URL (todos):** `perm:operational-context:companies:create` + `perm:operational-context:platform:administer`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`)
- ❌ **No pueden (responde `403`):** `supervisor.test` — sobre `operational-context` solo tiene `create`, `read`, `update`; le falta `administer`; `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `operational-context` solo tienen `read`; les falta `create`
- ℹ️ Para registrar o cambiar la organización o la ubicación, el token del usuario debe poder además **leer** en Party Identity y Geography: el servicio valida esas referencias con el mismo token. `administradores` y `supervisores` tienen esa lectura.
- ℹ️ Alcance de plataforma (Fase B, DS-05): registrar, inactivar y reactivar empresas y ver todas las empresas sin ser miembro. Solo lo concede `perm:all:all:all` (`administradores`); los comodines de lectura, creación o modificación **no** lo conceden.

**Por qué se hace así**

- `organization_identity_id` es **obligatorio**: la empresa se identifica por su organización.
- No se envían `timezone` ni `default_currency`: quedan `America/Bogota` y `COP`.
- Las coordenadas se envían como texto decimal (hasta 6 decimales, sin redondeo).

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<EMPRESA>",
  "organization_identity_id": "<ORG_EMPRESA>",
  "email": "contacto@comercializadora-ficticia.co",
  "phone": "+57 604 000 0001",
  "country_id": "<PAIS_CO>",
  "administrative_division_id": "<DIV_ANT>",
  "city_id": "<CIU_MED>",
  "latitude": "6.208000",
  "longitude": "-75.567000",
  "timezone": "America/Bogota",
  "default_currency": "COP",
  "status": "ACTIVE",
  "version": 1
}
```

**Guardar:** `id` → `<EMPRESA>`

## 2. Intentar registrar una empresa con una organización inexistente (rechazado)

```http
POST /api/v1/companies
```

```json
{
  "organization_identity_id": "7a1c0f10-0000-4000-8000-00000000dead"
}
```

**Permisos que exige la URL (todos):** `perm:operational-context:companies:create` + `perm:operational-context:platform:administer`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`)
- ❌ **No pueden (responde `403`):** `supervisor.test` — sobre `operational-context` solo tiene `create`, `read`, `update`; le falta `administer`; `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `operational-context` solo tienen `read`; les falta `create`
- ℹ️ Para registrar o cambiar la organización o la ubicación, el token del usuario debe poder además **leer** en Party Identity y Geography: el servicio valida esas referencias con el mismo token. `administradores` y `supervisores` tienen esa lectura.
- ℹ️ Alcance de plataforma (Fase B, DS-05): registrar, inactivar y reactivar empresas y ver todas las empresas sin ser miembro. Solo lo concede `perm:all:all:all` (`administradores`); los comodines de lectura, creación o modificación **no** lo conceden.

**Por qué se hace así**

- Party Identity responde `404`: la API responde `422 ORGANIZATION_IDENTITY_NOT_FOUND` y no guarda nada.

**Respuesta esperada (error) — `422 Unprocessable Content`** (abreviada)

```json
{
  "status": 422,
  "code": "OPERATIONAL_CONTEXT.ORGANIZATION_IDENTITY_NOT_FOUND",
  "detail": "La organización indicada no existe en Party Identity Service.",
  "errors": [
    {
      "field": "organization_identity_id",
      "message": "La organización indicada no existe en Party Identity Service.",
      "code": "ORGANIZATION_IDENTITY_NOT_FOUND"
    }
  ]
}
```

---

[← Paso anterior](02-consultar-ubicacion.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](04-consultar-y-modificar.md)
