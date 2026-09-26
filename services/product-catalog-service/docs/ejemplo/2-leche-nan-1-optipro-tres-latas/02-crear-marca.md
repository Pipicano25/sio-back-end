# Paso 02 de 12 — Crear la marca NAN

Ejercicio 2 — Leche NAN 1 Optipro: tres filas del Excel, un solo producto · [← Paso anterior](01-consultar-datos-base.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](03-crear-categorias.md)

**Objetivo:** Registrar la marca comercial.

**Deja guardado para los siguientes pasos:** `<MARCA_NAN>`

---

## 1. Crear la marca `NAN`

```http
POST /api/v1/brands
```

```json
{
  "code": "NAN",
  "name": "NAN",
  "description": "Línea de fórmulas infantiles de Nestlé."
}
```

**Permiso que exige la URL:** `perm:product-catalog:brands:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `create`

**Por qué se hace así**

- `NAN` es la marca que inicia el nombre; Nestlé (al final del nombre) es el fabricante.
- Se crea una sola vez y la comparten todos los productos NAN del Excel (NAN 2, NAN 3, NAN AR…).

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<MARCA_NAN>",
  "code": "NAN",
  "name": "NAN",
  "status": "ACTIVE"
}
```

**Guardar:** `id` → `<MARCA_NAN>`

---

> Si responde `409 DUPLICATE_CODE`, consulte `GET /api/v1/brands?code=NAN` y use ese `id`.

---

[← Paso anterior](01-consultar-datos-base.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](03-crear-categorias.md)
