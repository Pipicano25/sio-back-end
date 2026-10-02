# Paso 01 de 05 — Consultar el país y las reglas de Colombia

Ejercicio 1 — Reglas de identificación: crear, versionar y retirar · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](02-crear-regla.md)

**Objetivo:** Obtener `<PAIS_CO>` y ver las reglas `CC` que dejó la carga inicial.

**Deja guardado para los siguientes pasos:** `<PAIS_CO>`

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

## 2. Consultar las reglas activas de cédula (`CC`) de Colombia

```http
GET /api/v1/identification-type-rules?country_id=<PAIS_CO>&sigla=CC&is_active=true
```

**Permiso que exige la URL:** `perm:party-identity:identification_type_rules:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:party-identity:identification_type_rules:read`), `ventas.test` (por `perm:party-identity:identification_type_rules:read`), `reportes.test` (por `perm:party-identity:identification_type_rules:read`), `consulta.test` (por `perm:party-identity:identification_type_rules:read`)
- ❌ **No pueden (responde `403`):** `inventario.test` — no tiene ningún permiso sobre `party-identity`

**Por qué se hace así**

- Hay dos reglas `CC`: la cédula moderna (10 dígitos) y la antigua (3 a 8). Un número es válido si cumple **al menos una** de las reglas activas de la sigla.
- `is_active=true` excluye las reglas históricas.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "identification_type": "CITIZEN_ID_MODERN",
      "sigla": "CC",
      "number_pattern": "^[0-9]{10}$",
      "min_age_years": 18,
      "is_active": true
    },
    {
      "identification_type": "CITIZEN_ID_OLD",
      "sigla": "CC",
      "number_pattern": "^[0-9]{3,8}$",
      "min_age_years": 18,
      "is_active": true
    }
  ],
  "total_records": 2
}
```

---

[Orden del ejercicio](ORDEN.md) · [Paso siguiente →](02-crear-regla.md)
