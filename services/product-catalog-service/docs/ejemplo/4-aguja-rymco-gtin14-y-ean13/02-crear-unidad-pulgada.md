# Paso 02 de 11 — Crear la unidad pulgada (`PULG`)

Ejercicio 4 — Aguja hipodérmica 18G x 1½" Rymco, caja x 100 · [← Paso anterior](01-consultar-datos-base.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](03-crear-categorias.md)

**Objetivo:** Poder expresar la longitud de la aguja (1½").

**Deja guardado para los siguientes pasos:** `<PULG>`

---

## 1. Crear la unidad `PULG`

```http
POST /api/v1/units-of-measure
```

```json
{
  "code": "PULG",
  "name": "Pulgada",
  "symbol": "in",
  "measurement_type": "LENGTH",
  "allows_decimals": true
}
```

**Permiso que exige la URL:** `perm:product-catalog:units-of-measure:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `create`

**Por qué se hace así**

- Las agujas se identifican en pulgadas (`1 1/2` = 1.5"). Convertirlas a cm (3.81) haría el dato irreconocible para quien compra.
- `measurement_type: LENGTH` (mide longitud, como `M` y `CM`).
- `allows_decimals: true` por medidas como 1.5 o 0.5 pulgadas.
- `symbol: in` es el símbolo internacional de la pulgada.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<PULG>",
  "code": "PULG",
  "name": "Pulgada",
  "symbol": "in",
  "measurement_type": "LENGTH",
  "allows_decimals": true
}
```

**Guardar:** `id` → `<PULG>`

---

> Si responde `409 DUPLICATE_CODE`, consulte `GET /api/v1/units-of-measure?code=PULG` y use ese `id`.

---

[← Paso anterior](01-consultar-datos-base.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](03-crear-categorias.md)
