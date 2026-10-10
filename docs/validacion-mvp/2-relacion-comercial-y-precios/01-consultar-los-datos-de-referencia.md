# Paso 01 de 06 — Consultar los datos de referencia

Ejercicio 2 — Relación comercial y precios: proveedor, cliente, productos, adopción, presentaciones y listas · [Orden del ejercicio](ORDEN.md)

---

## 1. Consultar la unidad de medida UND en Product Catalog

Paso `C-00.5` · usuario **`admin.test`** · ítems de la FASE 10: 6

```http
GET http://127.0.0.1:8103/api/v1/units-of-measure?status=ACTIVE&page_size=100
```

**Permiso que exige la URL:** `perm:product-catalog:units-of-measure:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `compras.test` (por `perm:product-catalog:all:read`), `ventas.test` (por `perm:product-catalog:all:read`), `supervisor.test` (por `perm:all:all:read`), `consulta.test` (por `perm:product-catalog:units-of-measure:read`), `reportes.test` (por `perm:product-catalog:units-of-measure:read`), `inventario.test` (por `perm:product-catalog:all:read`)

**Respuesta esperada:** `200`

**Guardar:** `items[code=UND].id` → `<UNIDAD_UND>`

## 2. Consultar el tipo de condición de pago CREDIT en Payment Reference

Paso `C-00.6` · usuario **`admin.test`** · ítems de la FASE 10: 4

```http
GET http://127.0.0.1:8105/global-payment-condition-types?page_size=100
```

**Permiso que exige la URL:** `perm:payment-reference:global_payment_condition_types:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `compras.test` (por `perm:payment-reference:all:read`), `ventas.test` (por `perm:payment-reference:all:read`), `supervisor.test` (por `perm:all:all:read`), `consulta.test` (por `perm:payment-reference:global_payment_condition_types:read`), `reportes.test` (por `perm:payment-reference:global_payment_condition_types:read`)

**Respuesta esperada:** `200`

**Guardar:** `items[code=CREDIT].id` → `<TIPO_CREDITO>`
