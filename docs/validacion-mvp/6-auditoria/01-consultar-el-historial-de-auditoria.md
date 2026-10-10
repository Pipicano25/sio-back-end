# Paso 01 de 02 — Consultar el historial de auditoría

Ejercicio 6 — Auditoría del recorrido · [Orden del ejercicio](ORDEN.md)

---

## 1. Historial de auditoría de una entidad de la empresa A

Paso `U-01.empresa` · usuario **`admin.test`** · ítems de la FASE 10: 19

```http
GET http://127.0.0.1:8110/api/v1/companies/<EMPRESA_A>/entity-history/<TIPO_ENTIDAD>/<ID_ENTIDAD>
```

**Permiso que exige la URL:** `perm:audit:audit-events:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`)

**Por qué se hace así**

- Cada acción esperada aparece exactamente una vez, con su autor y en orden por `occurred_at`.

**Respuesta esperada:** `200`

## 2. Historial de auditoría de una entidad de plataforma

Paso `U-01.plataforma` · usuario **`admin.test`** · ítems de la FASE 10: 19

```http
GET http://127.0.0.1:8110/api/v1/platform-entity-history/<TIPO_ENTIDAD>/<ID_ENTIDAD>
```

**Permiso que exige la URL:** `perm:audit:platform-events:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`)

**Por qué se hace así**

- Identidades y productos globales generan eventos de plataforma (sin empresa).

**Respuesta esperada:** `200`
