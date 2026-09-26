# Paso 09 de 12 — Crear la presentación

Ejercicio 3 — Pañal Winny Gold etapa 6 XXXG, paquete x 30 · [← Paso anterior](08-registrar-valores-de-atributos.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](10-registrar-codigos-de-barras.md)

**Objetivo:** Paquete x 30 pañales.

**Necesita (de pasos anteriores):** `<PRODUCTO>`, `<PACK>` — pasos [01](01-consultar-datos-base.md), [06](06-crear-producto.md)

**Deja guardado para los siguientes pasos:** `<PRES_PAQUETE_X30>`

---

## 1. Presentación `PAQUETE_X30`

```http
POST /api/v1/products/<PRODUCTO>/presentations
```

```json
{
  "code": "PAQUETE_X30",
  "name": "Paquete x 30 pañales",
  "packaging_type_id": "<PACK>",
  "base_quantity": 30,
  "display_order": 1,
  "is_base": false
}
```

**Permiso que exige la URL:** `perm:product-catalog:products:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Todo lo que se agrega **dentro** de un producto (categorías, valores, presentaciones, códigos, grupos, imágenes) exige `update` sobre `products`.

**Por qué se hace así**

- `base_quantity: 30`: un paquete = 30 pañales (`Contenido Interno = 30`).
- `is_base: false` y no se crea la presentación "unidad": el Excel no indica que el pañal se venda suelto. Si una farmacia lo vendiera suelto, se agregaría después una presentación `UNIDAD` con `is_base: true` y `base_quantity: 1`.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<PRES_PAQUETE_X30>",
  "code": "PAQUETE_X30",
  "name": "Paquete x 30 pañales",
  "packaging_type_id": "<PACK>",
  "base_quantity": "30.00000000",
  "is_base": false,
  "eligible_for_adoption": true
}
```

**Guardar:** `id` → `<PRES_PAQUETE_X30>`

---

[← Paso anterior](08-registrar-valores-de-atributos.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](10-registrar-codigos-de-barras.md)
