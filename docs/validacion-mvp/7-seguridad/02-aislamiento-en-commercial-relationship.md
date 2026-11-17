# Paso 02 de 12 — Aislamiento en Commercial Relationship

Ejercicio 7 — Seguridad entre empresas y permisos · [Orden del ejercicio](ORDEN.md)

---

## 1. inventario.test consulta los clientes de A

Paso `I-02.clientes` · usuario **`inventario.test`** · ítems de la FASE 10: 21

```http
GET http://127.0.0.1:8106/api/v1/companies/<EMPRESA_A>/company-customers
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_customers:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `compras.test` (por `perm:commercial-relationship:company_customers:read`), `ventas.test` (por `perm:commercial-relationship:company_customers:read`), `supervisor.test` (por `perm:commercial-relationship:all:read`), `inventario.test` (por `perm:commercial-relationship:company_customers:read`)

**Por qué se hace así**

- El usuario tiene el permiso, pero no es miembro de la empresa: el servicio responde 404 sin revelar si el recurso existe.

**Respuesta esperada:** `404`

## 2. inventario.test consulta los proveedores de A

Paso `I-02.proveedores` · usuario **`inventario.test`** · ítems de la FASE 10: 21

```http
GET http://127.0.0.1:8106/api/v1/companies/<EMPRESA_A>/company-suppliers
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_suppliers:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `compras.test` (por `perm:commercial-relationship:company_suppliers:read`), `ventas.test` (por `perm:commercial-relationship:company_suppliers:read`), `supervisor.test` (por `perm:commercial-relationship:all:read`), `inventario.test` (por `perm:commercial-relationship:company_suppliers:read`)

**Por qué se hace así**

- El usuario tiene el permiso, pero no es miembro de la empresa: el servicio responde 404 sin revelar si el recurso existe.

**Respuesta esperada:** `404`

## 3. inventario.test consulta los productos de A

Paso `I-02.productos` · usuario **`inventario.test`** · ítems de la FASE 10: 21

```http
GET http://127.0.0.1:8106/api/v1/companies/<EMPRESA_A>/company-products
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_products:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `compras.test` (por `perm:commercial-relationship:company_products:read`), `ventas.test` (por `perm:commercial-relationship:company_products:read`), `supervisor.test` (por `perm:commercial-relationship:all:read`), `inventario.test` (por `perm:commercial-relationship:company_products:read`)

**Por qué se hace así**

- El usuario tiene el permiso, pero no es miembro de la empresa: el servicio responde 404 sin revelar si el recurso existe.

**Respuesta esperada:** `404`

## 4. inventario.test consulta las listas de precios de A

Paso `I-02.listas` · usuario **`inventario.test`** · ítems de la FASE 10: 21

```http
GET http://127.0.0.1:8106/api/v1/companies/<EMPRESA_A>/price-lists
```

**Permiso que exige la URL:** `perm:commercial-relationship:price_lists:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `compras.test` (por `perm:commercial-relationship:price_lists:read`), `ventas.test` (por `perm:commercial-relationship:price_lists:read`), `supervisor.test` (por `perm:commercial-relationship:all:read`), `inventario.test` (por `perm:commercial-relationship:price_lists:read`)

**Por qué se hace así**

- El usuario tiene el permiso, pero no es miembro de la empresa: el servicio responde 404 sin revelar si el recurso existe.

**Respuesta esperada:** `404`
