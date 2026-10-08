# Paso 02 de 07 — Adoptar el acetaminofén (fila 40)

Ejercicio 1 — Adopción de productos del Excel · [← Paso anterior](01-consultar-datos-base.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](03-adoptar-aguja.md)

**Objetivo:** Adoptar el producto con lotes y vencimiento.

**Necesita (de pasos anteriores):** `<EMPRESA>`, `<GP_ACETAMINOFEN>` — pasos [01](01-consultar-datos-base.md)

**Deja guardado para los siguientes pasos:** `<CP_ACETAMINOFEN>`

---

## 1. Adoptar el acetaminofén

```http
POST /api/v1/companies/<EMPRESA>/company-products
```

```json
{
  "global_product_id": "<GP_ACETAMINOFEN>",
  "internal_code": "000045",
  "reference_code": "48691",
  "display_name": "ACETAMINOFEN (ADOREM) 500MG TABLETA CAJAX100 SIEGFRIED",
  "short_name": "ACETAMINOFEN",
  "currency_code": "COP",
  "inventory_control_enabled": true,
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

- `Código` 000045 → `internal_code`; `Referencia` 48691 → `reference_code`.
- `Maneja Lotes` = S y `Maneja Fecha Vencimiento` = S → ambas banderas en `true`; exigen `inventory_control_enabled` (`Control Inventario` = S).
- Sin `sale_price` ni `reference_cost`: el Excel los trae vacíos; quedan en `0`. Los importes se devuelven como **texto decimal** (`"0.00"`), nunca como número.
- El servicio comprueba que el producto global esté `ACTIVE` y completo y registra su primer uso en Product Catalog **antes** de guardar.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<CP_ACETAMINOFEN>",
  "global_product_id": "<GP_ACETAMINOFEN>",
  "internal_code": "000045",
  "reference_code": "48691",
  "display_name": "ACETAMINOFEN (ADOREM) 500MG TABLETA CAJAX100 SIEGFRIED",
  "short_name": "ACETAMINOFEN",
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

**Guardar:** `id` → `<CP_ACETAMINOFEN>`

---

[← Paso anterior](01-consultar-datos-base.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](03-adoptar-aguja.md)
