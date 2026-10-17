# Paso 04 de 14 — Crear los atributos

Ejercicio 5 — Cepillo Colgate infantil pack x 2 (producto inactivo) · [← Paso anterior](03-crear-categorias.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](05-asociar-atributos-a-la-categoria.md)

**Objetivo:** Dureza de las cerdas (lista) y rango de edad (texto).

**Deja guardado para los siguientes pasos:** `<ATR_DUREZA_CERDAS>`, `<OPC_EXTRA_SUAVE>`, `<OPC_SUAVE>`, `<OPC_MEDIO>`, `<OPC_DURO>`, `<ATR_RANGO_EDAD>`

---

## 1. Crear el atributo `DUREZA_CERDAS` (lista de opciones)

```http
POST /api/v1/attribute-definitions
```

```json
{
  "code": "DUREZA_CERDAS",
  "name": "Dureza de las cerdas",
  "description": "Firmeza de las cerdas del cepillo.",
  "data_type": "OPTION"
}
```

**Permiso que exige la URL:** `perm:product-catalog:attribute-definitions:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `create`

**Por qué se hace así**

- Valores cerrados y conocidos: extra suave, suave, medio, duro.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<ATR_DUREZA_CERDAS>",
  "code": "DUREZA_CERDAS",
  "data_type": "OPTION"
}
```

**Guardar:** `id` → `<ATR_DUREZA_CERDAS>`

## 2. Opción `EXTRA_SUAVE`

```http
POST /api/v1/attribute-definitions/<ATR_DUREZA_CERDAS>/options
```

```json
{
  "code": "EXTRA_SUAVE",
  "name": "Extra suave",
  "display_order": 1
}
```

**Permiso que exige la URL:** `perm:product-catalog:attribute-definitions:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Crear una **opción** modifica la definición del atributo: exige `update`, no `create`.

**Por qué se hace así**

- Dureza de este producto ("EXTRA SUAVE" en el nombre del Excel).
- El código usa guion bajo (`EXTRA_SUAVE`); el nombre, texto legible.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<OPC_EXTRA_SUAVE>",
  "code": "EXTRA_SUAVE",
  "name": "Extra suave",
  "display_order": 1
}
```

**Guardar:** `id` → `<OPC_EXTRA_SUAVE>`

## 3. Opción `SUAVE`

```http
POST /api/v1/attribute-definitions/<ATR_DUREZA_CERDAS>/options
```

```json
{
  "code": "SUAVE",
  "name": "Suave",
  "display_order": 2
}
```

**Permiso que exige la URL:** `perm:product-catalog:attribute-definitions:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Crear una **opción** modifica la definición del atributo: exige `update`, no `create`.

**Por qué se hace así**

- Completa la lista para los demás cepillos del Excel.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<OPC_SUAVE>",
  "code": "SUAVE",
  "name": "Suave",
  "display_order": 2
}
```

**Guardar:** `id` → `<OPC_SUAVE>`

## 4. Opción `MEDIO`

```http
POST /api/v1/attribute-definitions/<ATR_DUREZA_CERDAS>/options
```

```json
{
  "code": "MEDIO",
  "name": "Medio",
  "display_order": 3
}
```

**Permiso que exige la URL:** `perm:product-catalog:attribute-definitions:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Crear una **opción** modifica la definición del atributo: exige `update`, no `create`.

**Por qué se hace así**

- Completa la lista para los demás cepillos del Excel.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<OPC_MEDIO>",
  "code": "MEDIO",
  "name": "Medio",
  "display_order": 3
}
```

**Guardar:** `id` → `<OPC_MEDIO>`

## 5. Opción `DURO`

```http
POST /api/v1/attribute-definitions/<ATR_DUREZA_CERDAS>/options
```

```json
{
  "code": "DURO",
  "name": "Duro",
  "display_order": 4
}
```

**Permiso que exige la URL:** `perm:product-catalog:attribute-definitions:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Crear una **opción** modifica la definición del atributo: exige `update`, no `create`.

**Por qué se hace así**

- Completa la lista para los demás cepillos del Excel.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<OPC_DURO>",
  "code": "DURO",
  "name": "Duro",
  "display_order": 4
}
```

**Guardar:** `id` → `<OPC_DURO>`

## 6. Crear el atributo `RANGO_EDAD` (texto)

```http
POST /api/v1/attribute-definitions
```

```json
{
  "code": "RANGO_EDAD",
  "name": "Rango de edad",
  "description": "Edad recomendada de uso indicada por el fabricante.",
  "data_type": "TEXT"
}
```

**Permiso que exige la URL:** `perm:product-catalog:attribute-definitions:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `create`

**Por qué se hace así**

- `TEXT` porque cada fabricante expresa el rango a su manera ("2-5 años", "6+ años", "0-2 años").

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<ATR_RANGO_EDAD>",
  "code": "RANGO_EDAD",
  "data_type": "TEXT"
}
```

**Guardar:** `id` → `<ATR_RANGO_EDAD>`

---

[← Paso anterior](03-crear-categorias.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](05-asociar-atributos-a-la-categoria.md)
