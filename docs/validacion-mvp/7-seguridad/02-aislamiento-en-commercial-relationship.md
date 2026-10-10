# Paso 02 de 12 — Aislamiento en Commercial Relationship

Ejercicio 7 — Seguridad entre empresas y permisos · [Orden del ejercicio](ORDEN.md)

---

## 1. reportes.test consulta los clientes de A

Paso `I-02.clientes` · usuario **`reportes.test`** · ítems de la FASE 10: 21

```http
GET http://127.0.0.1:8106/api/v1/companies/<EMPRESA_A>/company-customers
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_customers:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `compras.test` (por `perm:commercial-relationship:all:read`), `ventas.test` (por `perm:commercial-relationship:all:read`), `supervisor.test` (por `perm:all:all:read`), `consulta.test` (por `perm:commercial-relationship:company_customers:read`), `reportes.test` (por `perm:commercial-relationship:company_customers:read`)

**Por qué se hace así**

- El usuario tiene el permiso, pero no es miembro de la empresa: el servicio responde 404 sin revelar si el recurso existe.

**Respuesta esperada:** `404`

## 2. reportes.test consulta los proveedores de A

Paso `I-02.proveedores` · usuario **`reportes.test`** · ítems de la FASE 10: 21

```http
GET http://127.0.0.1:8106/api/v1/companies/<EMPRESA_A>/company-suppliers
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_suppliers:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `compras.test` (por `perm:commercial-relationship:all:read`), `ventas.test` (por `perm:commercial-relationship:all:read`), `supervisor.test` (por `perm:all:all:read`), `consulta.test` (por `perm:commercial-relationship:company_suppliers:read`), `reportes.test` (por `perm:commercial-relationship:company_suppliers:read`)

**Por qué se hace así**

- El usuario tiene el permiso, pero no es miembro de la empresa: el servicio responde 404 sin revelar si el recurso existe.

**Respuesta esperada:** `404`

## 3. reportes.test consulta los productos de A

Paso `I-02.productos` · usuario **`reportes.test`** · ítems de la FASE 10: 21

```http
GET http://127.0.0.1:8106/api/v1/companies/<EMPRESA_A>/company-products
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_products:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `compras.test` (por `perm:commercial-relationship:all:read`), `ventas.test` (por `perm:commercial-relationship:all:read`), `supervisor.test` (por `perm:all:all:read`), `consulta.test` (por `perm:commercial-relationship:company_products:read`), `reportes.test` (por `perm:commercial-relationship:company_products:read`), `inventario.test` (por `perm:commercial-relationship:company_products:read`)

**Por qué se hace así**

- El usuario tiene el permiso, pero no es miembro de la empresa: el servicio responde 404 sin revelar si el recurso existe.

**Respuesta esperada:** `404`

## 4. reportes.test consulta las listas de precios de A

Paso `I-02.listas` · usuario **`reportes.test`** · ítems de la FASE 10: 21

```http
GET http://127.0.0.1:8106/api/v1/companies/<EMPRESA_A>/price-lists
```

**Permiso que exige la URL:** `perm:commercial-relationship:price_lists:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `compras.test` (por `perm:commercial-relationship:all:read`), `ventas.test` (por `perm:commercial-relationship:all:read`), `supervisor.test` (por `perm:all:all:read`), `consulta.test` (por `perm:commercial-relationship:price_lists:read`), `reportes.test` (por `perm:commercial-relationship:price_lists:read`)

**Por qué se hace así**

- El usuario tiene el permiso, pero no es miembro de la empresa: el servicio responde 404 sin revelar si el recurso existe.

**Respuesta esperada:** `404`
