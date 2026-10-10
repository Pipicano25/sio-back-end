# Paso 04 de 12 — Aislamiento en Sales

Ejercicio 7 — Seguridad entre empresas y permisos · [Orden del ejercicio](ORDEN.md)

---

## 1. reportes.test consulta las ventas de A

Paso `I-04.ventas` · usuario **`reportes.test`** · ítems de la FASE 10: 21

```http
GET http://127.0.0.1:8108/api/v1/companies/<EMPRESA_A>/sales
```

**Permiso que exige la URL:** `perm:sales:sales:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `ventas.test` (por `perm:sales:all:read`), `supervisor.test` (por `perm:all:all:read`), `consulta.test` (por `perm:sales:sales:read`), `reportes.test` (por `perm:sales:sales:read`)

**Por qué se hace así**

- El usuario tiene el permiso, pero no es miembro de la empresa: el servicio responde 404 sin revelar si el recurso existe.

**Respuesta esperada:** `404`

## 2. reportes.test consulta la venta V2

Paso `I-04.venta` · usuario **`reportes.test`** · ítems de la FASE 10: 21

```http
GET http://127.0.0.1:8108/api/v1/companies/<EMPRESA_A>/sales/<VENTA_2>
```

**Permiso que exige la URL:** `perm:sales:sales:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `ventas.test` (por `perm:sales:all:read`), `supervisor.test` (por `perm:all:all:read`), `consulta.test` (por `perm:sales:sales:read`), `reportes.test` (por `perm:sales:sales:read`)

**Por qué se hace así**

- El usuario tiene el permiso, pero no es miembro de la empresa: el servicio responde 404 sin revelar si el recurso existe.

**Respuesta esperada:** `404`
