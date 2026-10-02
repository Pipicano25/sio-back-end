# Paso 01 de 03 — Consultar referencias externas

Ejercicio 5 — Perfil de contacto de una persona: cliente persona natural e inactivación · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](02-registrar-persona-y-perfil.md)

**Objetivo:** Obtener `<PAIS_CO>` y `<EMPRESA>`.

**Deja guardado para los siguientes pasos:** `<PAIS_CO>`, `<EMPRESA>`

---

## 1. Consultar el país Colombia en Geography Service

> **Otro servicio:** esta llamada va a **Geography Service**, no a Party Identity.

```http
GET http://localhost:8000/global-countries?iso3_code=COL
```

**Permiso que exige la URL:** `perm:geography:global_countries:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:geography:all:read`), `ventas.test` (por `perm:geography:all:read`), `inventario.test` (por `perm:geography:all:read`), `reportes.test` (por `perm:geography:global_countries:read`), `consulta.test` (por `perm:geography:global_countries:read`)

**Por qué se hace así**

- Party Identity no guarda países: solo guarda el `id` del país registrado en **Geography Service** (puerto `8000`) y lo valida contra él al crear o al cambiar la identificación.
- Se filtra por `iso3_code`, que es estable entre entornos; el `id` puede cambiar de una base a otra.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "id": "<PAIS_CO>",
      "iso2_code": "CO",
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

## 2. Consultar la empresa desde la que se confirma en Operational Context

> **Otro servicio:** esta llamada va a **Geography Service**, no a Party Identity.

```http
GET http://localhost:8004/api/v1/companies?status=ACTIVE
```

**Permiso que exige la URL:** `perm:operational-context:companies:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:operational-context:all:read`), `ventas.test` (por `perm:operational-context:all:read`), `inventario.test` (por `perm:operational-context:all:read`), `reportes.test` (por `perm:operational-context:companies:read`), `consulta.test` (por `perm:operational-context:companies:read`)

**Por qué se hace así**

- El perfil de contacto se confirma **desde una empresa**: Party Identity guarda solo el `id` de la empresa (`confirmed_by_company_id`) y el del usuario operativo que confirmó (`confirmed_by_user_id`).
- Para confirmar, el usuario debe tener una **membresía `ACTIVE`** en esa empresa (Operational Context, ejercicio 4 de su `docs/ejemplo/`). Party Identity la comprueba con su propio cliente técnico; el usuario **no** necesita permisos de Operational Context para confirmar.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "id": "<EMPRESA>",
      "status": "ACTIVE"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

**Guardar:** `items[0].id` → `<EMPRESA>`

---

[Orden del ejercicio](ORDEN.md) · [Paso siguiente →](02-registrar-persona-y-perfil.md)
