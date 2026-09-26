# Paso 03 de 13 — Crear la marca Adorem

Ejercicio 1 — Acetaminofén Adorem 500 mg, caja x 100 · [← Paso anterior](02-crear-unidad-mg.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](04-crear-categorias.md)

**Objetivo:** Registrar la marca comercial que el Excel esconde dentro del nombre.

**Deja guardado para los siguientes pasos:** `<MARCA_ADOREM>`

---

## 1. Crear la marca `ADOREM`

```http
POST /api/v1/brands
```

```json
{
  "code": "ADOREM",
  "name": "Adorem",
  "description": "Marca comercial de acetaminofén de Siegfried."
}
```

**Permiso que exige la URL:** `perm:product-catalog:brands:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `create`

**Por qué se hace así**

- En el nombre del Excel, lo que va entre paréntesis — `(ADOREM)` — es la marca comercial del medicamento.
- La columna `Nombre Marca` no sirve: vale `GENERAL` en 16 883 de las 16 889 filas.
- La marca es distinta del fabricante: Adorem es la marca, Siegfried quien lo fabrica.
- `code` se guarda en mayúsculas y no se puede cambiar; `name` y `description` sí.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<MARCA_ADOREM>",
  "code": "ADOREM",
  "name": "Adorem",
  "status": "ACTIVE"
}
```

**Guardar:** `id` → `<MARCA_ADOREM>`

---

[← Paso anterior](02-crear-unidad-mg.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](04-crear-categorias.md)
