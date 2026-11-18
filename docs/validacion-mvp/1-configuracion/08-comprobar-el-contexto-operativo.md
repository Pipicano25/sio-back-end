# Paso 08 de 08 — Comprobar el contexto operativo

Ejercicio 1 — Configuración de la empresa: organizaciones, personas, empresas, sucursales y usuarios operativos · [Orden del ejercicio](ORDEN.md)

---

## 1. Consultar el contexto operativo de admin.sio

Paso `C-07.admin` · usuario **`admin.sio`** · ítems de la FASE 10: 3

```http
GET http://127.0.0.1:8104/api/v1/me/operational-context
```

**Permiso que exige la URL:** `perm:operational-context:application_users:read`

- ✅ **Pueden:** `admin.sio` (por `perm:all:all:all`), `admin.dao` (por `perm:operational-context:all:read`), `operario.dao` (por `perm:operational-context:all:read`)

**Por qué se hace así**

- Cada usuario de A ve su membresía en A y, si está asignado, la sucursal A1 permitida.

**Respuesta esperada:** `200`

## 2. Consultar el contexto operativo de operario.dao

Paso `C-07.operario` · usuario **`operario.dao`** · ítems de la FASE 10: 3

```http
GET http://127.0.0.1:8104/api/v1/me/operational-context
```

**Permiso que exige la URL:** `perm:operational-context:application_users:read`

- ✅ **Pueden:** `admin.sio` (por `perm:all:all:all`), `admin.dao` (por `perm:operational-context:all:read`), `operario.dao` (por `perm:operational-context:all:read`)

**Por qué se hace así**

- Cada usuario de A ve su membresía en A y, si está asignado, la sucursal A1 permitida.

**Respuesta esperada:** `200`
