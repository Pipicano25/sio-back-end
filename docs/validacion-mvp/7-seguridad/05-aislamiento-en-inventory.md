# Paso 05 de 12 — Aislamiento en Inventory

Ejercicio 7 — Seguridad entre empresas y permisos · [Orden del ejercicio](ORDEN.md)

---

## 1. inventario.test consulta los saldos de A1

Paso `I-05.saldos` · usuario **`inventario.test`** · ítems de la FASE 10: 21

```http
GET http://127.0.0.1:8109/api/v1/companies/<EMPRESA_A>/branches/<SUCURSAL_A1>/balances
```

**Permiso que exige la URL:** `perm:inventory:balances:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `inventario.test` (por `perm:inventory:balances:read`)

**Por qué se hace así**

- El usuario tiene el permiso, pero no es miembro de la empresa: el servicio responde 404 sin revelar si el recurso existe.

**Respuesta esperada:** `404`

## 2. inventario.test consulta el kardex del producto A en A1

Paso `I-05.kardex` · usuario **`inventario.test`** · ítems de la FASE 10: 21

```http
GET http://127.0.0.1:8109/api/v1/companies/<EMPRESA_A>/branches/<SUCURSAL_A1>/kardex/<PRODUCTO_EMPRESA_A>
```

**Permiso que exige la URL:** `perm:inventory:movements:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `inventario.test` (por `perm:inventory:movements:read`)

**Por qué se hace así**

- El usuario tiene el permiso, pero no es miembro de la empresa: el servicio responde 404 sin revelar si el recurso existe.

**Respuesta esperada:** `404`

## 3. inventario.test consulta la valoración de A1

Paso `I-05.valoracion` · usuario **`inventario.test`** · ítems de la FASE 10: 21

```http
GET http://127.0.0.1:8109/api/v1/companies/<EMPRESA_A>/branches/<SUCURSAL_A1>/valuation
```

**Permiso que exige la URL:** `perm:inventory:valuation:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `inventario.test` (por `perm:inventory:valuation:read`)

**Por qué se hace así**

- El usuario tiene el permiso, pero no es miembro de la empresa: el servicio responde 404 sin revelar si el recurso existe.

**Respuesta esperada:** `404`

## 4. inventario.test intenta un ajuste en A1

Paso `I-05.ajuste` · usuario **`inventario.test`** · ítems de la FASE 10: 21

```http
POST http://127.0.0.1:8109/api/v1/companies/<EMPRESA_A>/inventory-adjustments
```

```json
{
  "adjustment_key": "<CLAVE_AJUSTE>",
  "branch_id": "<SUCURSAL_A1>",
  "company_product_id": "<PRODUCTO_EMPRESA_A>",
  "adjustment_type": "NEGATIVE",
  "quantity": "1",
  "reason": "Intento de ajuste ajeno (validación MVP <RUN_ID>, dato ficticio)"
}
```

**Permiso que exige la URL:** `perm:inventory:adjustments:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`), `inventario.test` (por `perm:inventory:adjustments:create`)

**Por qué se hace así**

- El usuario tiene el permiso, pero no es miembro de la empresa: el servicio responde 404 sin revelar si el recurso existe.

**Respuesta esperada:** `404`
