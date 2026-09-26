# Paso 02 de 13 — Crear la unidad de medida miligramo (`MG`)

Ejercicio 1 — Acetaminofén Adorem 500 mg, caja x 100 · [← Paso anterior](01-consultar-datos-base.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](03-crear-marca.md)

**Objetivo:** Tener una unidad para expresar la concentración (500 mg).

**Deja guardado para los siguientes pasos:** `<MG>`

---

## 1. Crear la unidad `MG`

```http
POST /api/v1/units-of-measure
```

```json
{
  "code": "MG",
  "name": "Miligramo",
  "symbol": "mg",
  "measurement_type": "MASS",
  "allows_decimals": true
}
```

**Permiso que exige la URL:** `perm:product-catalog:units-of-measure:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `create`

**Por qué se hace así**

- La carga inicial trae `G` y `KG`, pero no `MG`. Las concentraciones de medicamentos se expresan en mg.
- `measurement_type: MASS` porque el miligramo mide masa, igual que `G` y `KG`.
- `allows_decimals: true` porque hay concentraciones como 2.5 mg o 0.25 mg.
- `code`, `measurement_type` y `allows_decimals` **no se pueden cambiar después** (son inmutables): revíselos antes de enviar.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<MG>",
  "code": "MG",
  "name": "Miligramo",
  "symbol": "mg",
  "measurement_type": "MASS",
  "allows_decimals": true,
  "status": "ACTIVE"
}
```

**Guardar:** `id` → `<MG>`

---

> Si responde `409 DUPLICATE_CODE`, la unidad ya existe (por ejemplo, de una carga anterior): consúltela con `GET /api/v1/units-of-measure?code=MG` y use ese `id` como `<MG>`.

---

[← Paso anterior](01-consultar-datos-base.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](03-crear-marca.md)
