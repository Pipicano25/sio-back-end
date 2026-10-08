# Paso 03 de 07 — Adoptar la aguja (fila 413)

Ejercicio 1 — Adopción de productos del Excel · [← Paso anterior](02-adoptar-acetaminofen.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](04-rechazos.md)

**Objetivo:** Adoptar un segundo producto de la misma empresa.

**Necesita (de pasos anteriores):** `<EMPRESA>`, `<GP_AGUJA>` — pasos [01](01-consultar-datos-base.md)

**Deja guardado para los siguientes pasos:** `<CP_AGUJA>`

---

## 1. Adoptar la aguja

```http
POST /api/v1/companies/<EMPRESA>/company-products
```

```json
{
  "global_product_id": "<GP_AGUJA>",
  "internal_code": "000537",
  "reference_code": "71430",
  "display_name": "AGUJA 18GX1 1/2 CAJAX100 RFZC18B RYMCO",
  "short_name": "AGUJA 18GX1 1/2",
  "currency_code": "COP",
  "lot_tracking_enabled": true,
  "expiration_tracking_enabled": true
}
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_products:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `company_products` solo tienen `read`; les falta `create`
- ℹ️ Adoptar no exige permisos en Product Catalog al usuario: la elegibilidad y el registro de primer uso los hace el servicio con su propia identidad técnica (cliente `commercial-relationship-service`).
- 🔒 Aislamiento por empresa: además del permiso, el usuario debe tener membresía `ACTIVE` en la empresa (según Operational Context). Si no, la URL responde `404`, igual que un `id` inexistente, **también para `admin.test`** (DS-03).

**Por qué se hace así**

- `RFZC18B` dentro del nombre es la referencia **del fabricante** (es un identificador del producto global en Product Catalog); la columna `Referencia` 71430 es de la empresa.
- `inventory_control_enabled` se omite: por defecto es `true`.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<CP_AGUJA>",
  "global_product_id": "<GP_AGUJA>",
  "internal_code": "000537",
  "reference_code": "71430",
  "display_name": "AGUJA 18GX1 1/2 CAJAX100 RFZC18B RYMCO",
  "short_name": "AGUJA 18GX1 1/2",
  "sale_price": "0.00",
  "currency_code": "COP",
  "reference_cost": "0.0000",
  "inventory_control_enabled": true,
  "lot_tracking_enabled": true,
  "expiration_tracking_enabled": true,
  "is_purchasable": true,
  "is_sellable": true,
  "status": "ACTIVE",
  "version": 1
}
```

**Guardar:** `id` → `<CP_AGUJA>`

---

[← Paso anterior](02-adoptar-acetaminofen.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](04-rechazos.md)
