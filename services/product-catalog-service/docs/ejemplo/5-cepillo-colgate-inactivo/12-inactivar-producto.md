# Paso 12 de 13 — Inactivar el producto (`Estado = I`)

Ejercicio 5 — Cepillo Colgate infantil pack x 2 (producto inactivo) · [← Paso anterior](11-crear-y-asignar-grupos.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](13-verificar-producto-inactivo.md)

**Objetivo:** Comprobar que quedó completo y luego inactivarlo.

**Necesita (de pasos anteriores):** `<PRODUCTO>` — pasos [06](06-crear-producto.md)

---

## 1. Consultar el producto antes de inactivar

```http
GET /api/v1/products/<PRODUCTO>
```

**Permiso que exige la URL:** `perm:product-catalog:products:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:product-catalog:all:read`), `ventas.test` (por `perm:product-catalog:all:read`), `inventario.test` (por `perm:product-catalog:all:read`), `reportes.test` (por `perm:all:all:read`), `consulta.test` (por `perm:all:all:read`)

**Por qué se hace así**

- Se necesita la `version` actual: la inactivación la exige para evitar pisar un cambio de otra persona (si no coincide, `409 VERSION_CONFLICT`).
- Se ve que está completo y elegible.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "version": 1,
  "status": "ACTIVE",
  "completeness": {
    "is_complete": true,
    "issues": [],
    "missing_attribute_definition_ids": [],
    "out_of_classification_value_ids": []
  },
  "eligible_for_adoption": true
}
```

## 2. Inactivar

```http
POST /api/v1/products/<PRODUCTO>/deactivate
```

```json
{
  "version": 1
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:deactivate`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`)
- ❌ **No pueden (responde `403`):** `supervisor.test` — sobre `product-catalog` solo tiene `create`, `read`, `update`; le falta `deactivate`; `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `deactivate`
- ℹ️ Inactivar es una acción propia (`deactivate`): no la cubren `create` ni `update`.

**Por qué se hace así**

- `version` es la que devolvió la consulta anterior (aquí `1`: asignar categorías, presentaciones o códigos no cambia la versión del producto; solo la cambian `PUT` y las acciones de estado).
- **No hay cascada**: presentaciones, códigos, grupos e imagen siguen `ACTIVE`.
- El producto sigue `is_complete: true`, pero `eligible_for_adoption: false`: ninguna empresa lo puede adoptar.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "version": 2,
  "status": "INACTIVE",
  "completeness": {
    "is_complete": true,
    "issues": [],
    "missing_attribute_definition_ids": [],
    "out_of_classification_value_ids": []
  },
  "eligible_for_adoption": false
}
```

---

[← Paso anterior](11-crear-y-asignar-grupos.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](13-verificar-producto-inactivo.md)
