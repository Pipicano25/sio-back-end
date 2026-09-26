# Paso 02 de 13 — Crear la marca Colgate

Ejercicio 5 — Cepillo Colgate infantil pack x 2 (producto inactivo) · [← Paso anterior](01-consultar-datos-base.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](03-crear-categorias.md)

**Objetivo:** Registrar la marca comercial.

**Deja guardado para los siguientes pasos:** `<MARCA_COLGATE>`

---

## 1. Crear la marca `COLGATE`

```http
POST /api/v1/brands
```

```json
{
  "code": "COLGATE",
  "name": "Colgate"
}
```

**Permiso que exige la URL:** `perm:product-catalog:brands:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `create`

**Por qué se hace así**

- La marca es Colgate; el fabricante es Colgate-Palmolive (`Grupo 4`). Aquí coinciden en nombre, pero siguen siendo datos distintos: la marca es del catálogo y el fabricante de Party Identity.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<MARCA_COLGATE>",
  "code": "COLGATE",
  "name": "Colgate"
}
```

**Guardar:** `id` → `<MARCA_COLGATE>`

---

> Si responde `409 DUPLICATE_CODE`, consulte `GET /api/v1/brands?code=COLGATE` y use ese `id`.

---

[← Paso anterior](01-consultar-datos-base.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](03-crear-categorias.md)
