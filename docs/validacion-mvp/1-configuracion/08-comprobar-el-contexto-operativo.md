# Paso 08 de 08 — Comprobar el contexto operativo

Ejercicio 1 — Configuración de la empresa: organizaciones, personas, empresas, sucursales y usuarios operativos · [Orden del ejercicio](ORDEN.md)

---

## 1. Consultar el contexto operativo de admin.test

Paso `C-07.admin` · usuario **`admin.test`** · ítems de la FASE 10: 3

```http
GET http://127.0.0.1:8104/api/v1/me/operational-context
```

**Permiso que exige la URL:** `perm:operational-context:application_users:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `compras.test` (por `perm:operational-context:all:read`), `ventas.test` (por `perm:operational-context:all:read`), `supervisor.test` (por `perm:all:all:read`), `consulta.test` (por `perm:operational-context:application_users:read`), `reportes.test` (por `perm:operational-context:application_users:read`), `inventario.test` (por `perm:operational-context:all:read`)

**Por qué se hace así**

- Cada usuario de A ve su membresía en A y, si está asignado, la sucursal A1 permitida.

**Respuesta esperada:** `200`

## 2. Consultar el contexto operativo de compras.test

Paso `C-07.compras` · usuario **`compras.test`** · ítems de la FASE 10: 3

```http
GET http://127.0.0.1:8104/api/v1/me/operational-context
```

**Permiso que exige la URL:** `perm:operational-context:application_users:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `compras.test` (por `perm:operational-context:all:read`), `ventas.test` (por `perm:operational-context:all:read`), `supervisor.test` (por `perm:all:all:read`), `consulta.test` (por `perm:operational-context:application_users:read`), `reportes.test` (por `perm:operational-context:application_users:read`), `inventario.test` (por `perm:operational-context:all:read`)

**Por qué se hace así**

- Cada usuario de A ve su membresía en A y, si está asignado, la sucursal A1 permitida.

**Respuesta esperada:** `200`

## 3. Consultar el contexto operativo de ventas.test

Paso `C-07.ventas` · usuario **`ventas.test`** · ítems de la FASE 10: 3

```http
GET http://127.0.0.1:8104/api/v1/me/operational-context
```

**Permiso que exige la URL:** `perm:operational-context:application_users:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `compras.test` (por `perm:operational-context:all:read`), `ventas.test` (por `perm:operational-context:all:read`), `supervisor.test` (por `perm:all:all:read`), `consulta.test` (por `perm:operational-context:application_users:read`), `reportes.test` (por `perm:operational-context:application_users:read`), `inventario.test` (por `perm:operational-context:all:read`)

**Por qué se hace así**

- Cada usuario de A ve su membresía en A y, si está asignado, la sucursal A1 permitida.

**Respuesta esperada:** `200`

## 4. Consultar el contexto operativo de supervisor.test

Paso `C-07.supervisor` · usuario **`supervisor.test`** · ítems de la FASE 10: 3

```http
GET http://127.0.0.1:8104/api/v1/me/operational-context
```

**Permiso que exige la URL:** `perm:operational-context:application_users:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `compras.test` (por `perm:operational-context:all:read`), `ventas.test` (por `perm:operational-context:all:read`), `supervisor.test` (por `perm:all:all:read`), `consulta.test` (por `perm:operational-context:application_users:read`), `reportes.test` (por `perm:operational-context:application_users:read`), `inventario.test` (por `perm:operational-context:all:read`)

**Por qué se hace así**

- Cada usuario de A ve su membresía en A y, si está asignado, la sucursal A1 permitida.

**Respuesta esperada:** `200`

## 5. Consultar el contexto operativo de consulta.test

Paso `C-07.consulta` · usuario **`consulta.test`** · ítems de la FASE 10: 3

```http
GET http://127.0.0.1:8104/api/v1/me/operational-context
```

**Permiso que exige la URL:** `perm:operational-context:application_users:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `compras.test` (por `perm:operational-context:all:read`), `ventas.test` (por `perm:operational-context:all:read`), `supervisor.test` (por `perm:all:all:read`), `consulta.test` (por `perm:operational-context:application_users:read`), `reportes.test` (por `perm:operational-context:application_users:read`), `inventario.test` (por `perm:operational-context:all:read`)

**Por qué se hace así**

- Cada usuario de A ve su membresía en A y, si está asignado, la sucursal A1 permitida.

**Respuesta esperada:** `200`
