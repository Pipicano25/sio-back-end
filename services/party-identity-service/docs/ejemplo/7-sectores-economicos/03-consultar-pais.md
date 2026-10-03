# Paso 03 de 05 — Consultar el país

Ejercicio 7 — Sectores económicos: árbol CIIU, catálogo propio y sectores de una organización · [← Paso anterior](02-clasificacion-propia.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](04-asignar-sectores.md)

**Objetivo:** Obtener `<PAIS_CO>`.

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

---

[← Paso anterior](02-clasificacion-propia.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](04-asignar-sectores.md)
