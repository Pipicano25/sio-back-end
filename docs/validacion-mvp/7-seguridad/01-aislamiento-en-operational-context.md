# Paso 01 de 12 — Aislamiento en Operational Context

Ejercicio 7 — Seguridad entre empresas y permisos · [Orden del ejercicio](ORDEN.md)

---

## 1. inventario.test consulta la empresa A

Paso `I-01.empresa` · usuario **`inventario.test`** · ítems de la FASE 10: 21

```http
GET http://127.0.0.1:8104/api/v1/companies/<EMPRESA_A>
```

**Permiso que exige la URL:** `perm:operational-context:companies:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `compras.test` (por `perm:operational-context:all:read`), `ventas.test` (por `perm:operational-context:all:read`), `supervisor.test` (por `perm:operational-context:all:read`), `inventario.test` (por `perm:operational-context:all:read`)

**Por qué se hace así**

- El usuario tiene el permiso, pero no es miembro de la empresa: el servicio responde 404 sin revelar si el recurso existe.

**Respuesta esperada:** `404`

## 2. inventario.test consulta las sucursales de A

Paso `I-01.sucursales` · usuario **`inventario.test`** · ítems de la FASE 10: 21

```http
GET http://127.0.0.1:8104/api/v1/companies/<EMPRESA_A>/branches
```

**Permiso que exige la URL:** `perm:operational-context:branches:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `compras.test` (por `perm:operational-context:all:read`), `ventas.test` (por `perm:operational-context:all:read`), `supervisor.test` (por `perm:operational-context:all:read`), `inventario.test` (por `perm:operational-context:all:read`)

**Por qué se hace así**

- El usuario tiene el permiso, pero no es miembro de la empresa: el servicio responde 404 sin revelar si el recurso existe.

**Respuesta esperada:** `404`

## 3. inventario.test consulta los usuarios operativos de A

Paso `I-01.usuarios` · usuario **`inventario.test`** · ítems de la FASE 10: 21

```http
GET http://127.0.0.1:8104/api/v1/companies/<EMPRESA_A>/application-users
```

**Permiso que exige la URL:** `perm:operational-context:application_users:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `compras.test` (por `perm:operational-context:all:read`), `ventas.test` (por `perm:operational-context:all:read`), `supervisor.test` (por `perm:operational-context:all:read`), `inventario.test` (por `perm:operational-context:all:read`)

**Por qué se hace así**

- El usuario tiene el permiso, pero no es miembro de la empresa: el servicio responde 404 sin revelar si el recurso existe.

**Respuesta esperada:** `404`
