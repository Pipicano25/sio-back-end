# Paso 01 de 05 — Crear las secuencias de numeración

Ejercicio 3 — Compras e inventario: secuencias, compras de contado, confirmación, recepción física (entradas), saldos, kardex y capas · [Orden del ejercicio](ORDEN.md)

---

## 1. Crear la secuencia de numeración de compras

Paso `C-13.compras` · usuario **`admin.test`** · ítems de la FASE 10: 10

```http
POST http://127.0.0.1:8107/api/v1/companies/<EMPRESA_A>/purchase-sequences
```

```json
{
  "series_code": "MVP",
  "prefix": "CP",
  "separator": "-",
  "initial_number": 1,
  "number_length": 6,
  "reset_policy": "NEVER"
}
```

**Permiso que exige la URL:** `perm:purchase:purchase_sequences:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `compras.test` (por `perm:purchase:all:all`), `supervisor.test` (por `perm:all:all:create`)

**Por qué se hace así**

- La compra recibe su número oficial al confirmarse.

**Respuesta esperada:** `201`

**Guardar:** `id` → `<SECUENCIA_COMPRAS>`

**Auditoría que deja:** `CREATE_PURCHASE_SEQUENCE` (purchase)

## 2. Crear la secuencia de numeración de ventas

Paso `C-13.ventas` · usuario **`admin.test`** · ítems de la FASE 10: 15

```http
POST http://127.0.0.1:8108/api/v1/companies/<EMPRESA_A>/sale-sequences
```

```json
{
  "series_code": "MVP",
  "prefix": "FV",
  "separator": "-",
  "initial_number": 1,
  "number_length": 6,
  "reset_policy": "NEVER"
}
```

**Permiso que exige la URL:** `perm:sales:sale_sequences:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `ventas.test` (por `perm:sales:all:create`), `supervisor.test` (por `perm:all:all:create`)

**Respuesta esperada:** `201`

**Guardar:** `id` → `<SECUENCIA_VENTAS>`

**Auditoría que deja:** `CREATE_SALE_SEQUENCE` (sales)
