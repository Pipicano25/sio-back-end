# Paso 03 de 12 — Aislamiento en Purchase

Ejercicio 7 — Seguridad entre empresas y permisos · [Orden del ejercicio](ORDEN.md)

---

## 1. admin.dao consulta las compras de A

Paso `I-03.compras` · usuario **`admin.dao`** · ítems de la FASE 10: 21

```http
GET http://127.0.0.1:8107/api/v1/companies/<EMPRESA_A>/purchases
```

**Permiso que exige la URL:** `perm:purchase:purchases:read`

- ✅ **Pueden:** `admin.sio` (por `perm:all:all:all`), `admin.dao` (por `perm:purchase:all:all`), `operario.dao` (por `perm:purchase:purchases:read`)

**Por qué se hace así**

- El usuario tiene el permiso, pero no es miembro de la empresa: el servicio responde 404 sin revelar si el recurso existe.

**Respuesta esperada:** `404`

## 2. admin.dao consulta la compra P1

Paso `I-03.compra` · usuario **`admin.dao`** · ítems de la FASE 10: 21

```http
GET http://127.0.0.1:8107/api/v1/companies/<EMPRESA_A>/purchases/<COMPRA_1>
```

**Permiso que exige la URL:** `perm:purchase:purchases:read`

- ✅ **Pueden:** `admin.sio` (por `perm:all:all:all`), `admin.dao` (por `perm:purchase:all:all`), `operario.dao` (por `perm:purchase:purchases:read`)

**Por qué se hace así**

- El usuario tiene el permiso, pero no es miembro de la empresa: el servicio responde 404 sin revelar si el recurso existe.

**Respuesta esperada:** `404`
