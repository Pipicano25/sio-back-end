# Paso 06 de 12 — Aislamiento en Audit

Ejercicio 7 — Seguridad entre empresas y permisos · [Orden del ejercicio](ORDEN.md)

---

## 1. admin.test consulta los eventos de auditoría de B

Paso `I-06.eventos` · usuario **`admin.test`** · ítems de la FASE 10: 21

```http
GET http://127.0.0.1:8110/api/v1/companies/<EMPRESA_B>/audit-events
```

**Permiso que exige la URL:** `perm:audit:audit-events:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`)

**Por qué se hace así**

- El usuario tiene el permiso, pero no es miembro de la empresa: el servicio responde 404 sin revelar si el recurso existe.

**Respuesta esperada:** `404`

## 2. admin.test consulta el historial de la empresa B

Paso `I-06.historial` · usuario **`admin.test`** · ítems de la FASE 10: 21

```http
GET http://127.0.0.1:8110/api/v1/companies/<EMPRESA_B>/entity-history/Company/<EMPRESA_B>
```

**Permiso que exige la URL:** `perm:audit:audit-events:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`)

**Por qué se hace así**

- El usuario tiene el permiso, pero no es miembro de la empresa: el servicio responde 404 sin revelar si el recurso existe.

**Respuesta esperada:** `404`
