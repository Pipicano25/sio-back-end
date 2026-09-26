# Paso 02 de 12 — Crear la marca Winny

Ejercicio 3 — Pañal Winny Gold etapa 6 XXXG, paquete x 30 · [← Paso anterior](01-consultar-datos-base.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](03-crear-categorias.md)

**Objetivo:** Registrar la marca comercial.

**Deja guardado para los siguientes pasos:** `<MARCA_WINNY>`

---

## 1. Crear la marca `WINNY`

```http
POST /api/v1/brands
```

```json
{
  "code": "WINNY",
  "name": "Winny",
  "description": "Marca de pañales de Tecnoquímicas."
}
```

**Permiso que exige la URL:** `perm:product-catalog:brands:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `create`

**Por qué se hace así**

- La marca es `WINNY`; "Gold" es una línea de la marca y queda en el nombre del producto.
- El Excel lo confirma en `Grupo 4 = TECNOQUIMICAS (WINNY)`.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<MARCA_WINNY>",
  "code": "WINNY",
  "name": "Winny"
}
```

**Guardar:** `id` → `<MARCA_WINNY>`

---

> Si responde `409 DUPLICATE_CODE`, consulte `GET /api/v1/brands?code=WINNY` y use ese `id`.

---

[← Paso anterior](01-consultar-datos-base.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](03-crear-categorias.md)
