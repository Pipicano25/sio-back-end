# Paso 04 de 04 — Consultar y modificar la empresa

Ejercicio 1 — Empresa con su sede operativa principal · [← Paso anterior](03-registrar-empresa.md) · [Orden del ejercicio](ORDEN.md)

**Objetivo:** Leer la empresa, cambiar el teléfono con la versión vigente y buscarla por su organización.

**Necesita (de pasos anteriores):** `<EMPRESA>`, `<ORG_EMPRESA>`, `<PAIS_CO>`, `<DIV_ANT>`, `<CIU_MED>` — pasos [01](01-consultar-organizacion.md), [02](02-consultar-ubicacion.md), [03](03-registrar-empresa.md)

---

## 1. Consultar la empresa por su `id`

```http
GET /api/v1/companies/<EMPRESA>
```

**Permiso que exige la URL:** `perm:operational-context:companies:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:operational-context:all:read`), `ventas.test` (por `perm:operational-context:all:read`), `inventario.test` (por `perm:operational-context:all:read`), `reportes.test` (por `perm:all:all:read`), `consulta.test` (por `perm:all:all:read`)

**Por qué se hace así**

- Es la consulta que usan los demás servicios (contrato Provider).

**Respuesta esperada — `200 OK`** (abreviada)

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

## 2. Modificar el teléfono con la versión vigente

```http
PUT /api/v1/companies/<EMPRESA>
```

```json
{
  "organization_identity_id": "<ORG_EMPRESA>",
  "email": "contacto@comercializadora-ficticia.co",
  "phone": "+57 604 000 0002",
  "address_line": "Carrera Ficticia 43A # 1-50",
  "country_id": "<PAIS_CO>",
  "administrative_division_id": "<DIV_ANT>",
  "city_id": "<CIU_MED>",
  "postal_code": "050021",
  "latitude": "6.208000",
  "longitude": "-75.567000",
  "timezone": "America/Bogota",
  "default_currency": "COP",
  "version": 1
}
```

**Permiso que exige la URL:** `perm:operational-context:companies:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `operational-context` solo tienen `read`; les falta `update`

**Por qué se hace así**

- `PUT` reemplaza todos los campos: se envían de nuevo los que no cambian.
- No cambia la organización ni la ubicación: el servicio no vuelve a consultar Party Identity ni Geography.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "phone": "+57 604 000 0002",
  "version": 2
}
```

## 3. Buscar la empresa por su organización

```http
GET /api/v1/companies?organization_identity_id=<ORG_EMPRESA>
```

**Permiso que exige la URL:** `perm:operational-context:companies:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:operational-context:all:read`), `ventas.test` (por `perm:operational-context:all:read`), `inventario.test` (por `perm:operational-context:all:read`), `reportes.test` (por `perm:all:all:read`), `consulta.test` (por `perm:all:all:read`)

**Por qué se hace así**

- Para buscar por NIT o razón social se busca primero la organización en Party Identity (FR-054).

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "id": "<EMPRESA>",
      "status": "ACTIVE"
    }
  ],
  "total_records": 1
}
```

---

[← Paso anterior](03-registrar-empresa.md) · [Orden del ejercicio](ORDEN.md)
