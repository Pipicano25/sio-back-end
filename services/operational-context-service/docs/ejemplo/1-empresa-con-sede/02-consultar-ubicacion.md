# Paso 02 de 04 — Consultar la ubicación de la sede

Ejercicio 1 — Empresa con su sede operativa principal · [← Paso anterior](01-consultar-organizacion.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](03-registrar-empresa.md)

**Objetivo:** Obtener `<PAIS_CO>`, `<DIV_ANT>` y `<CIU_MED>`.

**Deja guardado para los siguientes pasos:** `<PAIS_CO>`, `<DIV_ANT>`, `<CIU_MED>`

---

## 1. Consultar el país Colombia en Geography Service

> **Otro servicio:** esta llamada va a **Geography Service**, no a Operational Context. No se ejecuta en la validación automática: su resultado se simula.

```http
GET http://localhost:8000/global-countries?iso3_code=COL
```

**Permiso que exige la URL:** `perm:geography:global_countries:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:geography:all:read`), `ventas.test` (por `perm:geography:all:read`), `inventario.test` (por `perm:geography:all:read`), `reportes.test` (por `perm:geography:global_countries:read`), `consulta.test` (por `perm:geography:global_countries:read`)

**Por qué se hace así**

- Operational Context no guarda países: guarda el `id` de Geography y lo valida al asignarlo.
- Se filtra por `iso3_code`, estable entre entornos; el `id` puede cambiar de una base a otra.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "id": "<PAIS_CO>",
      "iso3_code": "COL",
      "name": "Colombia",
      "status": "ACTIVE"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

**Guardar:** `items[0].id` → `<PAIS_CO>`

## 2. Consultar el departamento Antioquia en Geography Service

> **Otro servicio:** esta llamada va a **Geography Service**, no a Operational Context. No se ejecuta en la validación automática: su resultado se simula.

```http
GET http://localhost:8000/global-administrative-divisions?country_id=<PAIS_CO>&search=Antioquia
```

**Permiso que exige la URL:** `perm:geography:global_administrative_divisions:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:geography:all:read`), `ventas.test` (por `perm:geography:all:read`), `inventario.test` (por `perm:geography:all:read`), `reportes.test` (por `perm:geography:global_administrative_divisions:read`), `consulta.test` (por `perm:geography:global_administrative_divisions:read`)

**Por qué se hace así**

- La división administrativa debe pertenecer al país indicado (coherencia estricta, DS-05).

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "id": "<DIV_ANT>",
      "country_id": "<PAIS_CO>",
      "name": "Antioquia",
      "status": "ACTIVE"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

**Guardar:** `items[0].id` → `<DIV_ANT>`

## 3. Consultar la ciudad Medellín en Geography Service

> **Otro servicio:** esta llamada va a **Geography Service**, no a Operational Context. No se ejecuta en la validación automática: su resultado se simula.

```http
GET http://localhost:8000/global-cities?administrative_division_id=<DIV_ANT>&search=Medellín
```

**Permiso que exige la URL:** `perm:geography:global_cities:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:geography:all:read`), `ventas.test` (por `perm:geography:all:read`), `inventario.test` (por `perm:geography:all:read`), `reportes.test` (por `perm:geography:global_cities:read`), `consulta.test` (por `perm:geography:global_cities:read`)

**Por qué se hace así**

- La ciudad debe pertenecer al país y exactamente a la división enviada.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "id": "<CIU_MED>",
      "country_id": "<PAIS_CO>",
      "administrative_division_id": "<DIV_ANT>",
      "name": "Medellín",
      "status": "ACTIVE"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

**Guardar:** `items[0].id` → `<CIU_MED>`

---

[← Paso anterior](01-consultar-organizacion.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](03-registrar-empresa.md)
