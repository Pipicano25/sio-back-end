# Paso 02 de 02 — Datos protegidos y permiso de auditoría

Ejercicio 6 — Auditoría del recorrido · [Orden del ejercicio](ORDEN.md)

---

## 1. Consultar la auditoría como operario (rechazado)

Paso `U-02.vendedor` · usuario **`operario.dao`** · ítems de la FASE 10: 19

```http
GET http://127.0.0.1:8110/api/v1/companies/<EMPRESA_A>/audit-events
```

**Permiso que exige la URL:** `perm:audit:audit-events:read`

- ✅ **Pueden:** `admin.sio` (por `perm:all:all:all`), `admin.dao` (por `perm:audit:audit-events:read`)

**Por qué se hace así**

- `operario.dao` no tiene permiso de lectura de auditoría.

**Respuesta esperada:** `403`
