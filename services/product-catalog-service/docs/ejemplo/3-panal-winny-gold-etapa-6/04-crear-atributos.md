# Paso 04 de 12 — Crear los atributos y las opciones de talla

Ejercicio 3 — Pañal Winny Gold etapa 6 XXXG, paquete x 30 · [← Paso anterior](03-crear-categorias.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](05-asociar-atributos-a-la-categoria.md)

**Objetivo:** Definir la talla como lista cerrada y la etapa como número.

**Deja guardado para los siguientes pasos:** `<ATR_TALLA_PANAL>`, `<OPC_TALLA_RN>`, `<OPC_TALLA_P>`, `<OPC_TALLA_M>`, `<OPC_TALLA_G>`, `<OPC_TALLA_XG>`, `<OPC_TALLA_XXG>`, `<OPC_TALLA_XXXG>`, `<ATR_ETAPA_PANAL>`

---

## 1. Crear el atributo `TALLA_PANAL` (lista de opciones)

```http
POST /api/v1/attribute-definitions
```

```json
{
  "code": "TALLA_PANAL",
  "name": "Talla de pañal",
  "description": "Talla del pañal según el peso del bebé.",
  "data_type": "OPTION"
}
```

**Permiso que exige la URL:** `perm:product-catalog:attribute-definitions:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `create`

**Por qué se hace así**

- `OPTION` porque las tallas son una lista fija. Con `TEXT` aparecerían "XXXG", "XXX-G", "XXXL" y no se podría filtrar.
- El Excel tiene las columnas `Talla`/`Nombre Talla`, pero vacías: el dato hay que sacarlo del nombre.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<ATR_TALLA_PANAL>",
  "code": "TALLA_PANAL",
  "data_type": "OPTION"
}
```

**Guardar:** `id` → `<ATR_TALLA_PANAL>`

## 2. Opción `RN`

```http
POST /api/v1/attribute-definitions/<ATR_TALLA_PANAL>/options
```

```json
{
  "code": "RN",
  "name": "Recién nacido",
  "display_order": 1
}
```

**Permiso que exige la URL:** `perm:product-catalog:attribute-definitions:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Crear una **opción** modifica la definición del atributo: exige `update`, no `create`.

**Por qué se hace así**

- Completa la lista de tallas para los demás pañales del Excel (Huggies, Winny, Content…).
- `display_order` sigue el orden natural de tallas (de menor a mayor), no el alfabético.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<OPC_TALLA_RN>",
  "code": "RN",
  "name": "Recién nacido",
  "display_order": 1
}
```

**Guardar:** `id` → `<OPC_TALLA_RN>`

## 3. Opción `P`

```http
POST /api/v1/attribute-definitions/<ATR_TALLA_PANAL>/options
```

```json
{
  "code": "P",
  "name": "Pequeña",
  "display_order": 2
}
```

**Permiso que exige la URL:** `perm:product-catalog:attribute-definitions:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Crear una **opción** modifica la definición del atributo: exige `update`, no `create`.

**Por qué se hace así**

- Completa la lista de tallas para los demás pañales del Excel (Huggies, Winny, Content…).

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<OPC_TALLA_P>",
  "code": "P",
  "name": "Pequeña",
  "display_order": 2
}
```

**Guardar:** `id` → `<OPC_TALLA_P>`

## 4. Opción `M`

```http
POST /api/v1/attribute-definitions/<ATR_TALLA_PANAL>/options
```

```json
{
  "code": "M",
  "name": "Mediana",
  "display_order": 3
}
```

**Permiso que exige la URL:** `perm:product-catalog:attribute-definitions:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Crear una **opción** modifica la definición del atributo: exige `update`, no `create`.

**Por qué se hace así**

- Completa la lista de tallas para los demás pañales del Excel (Huggies, Winny, Content…).

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<OPC_TALLA_M>",
  "code": "M",
  "name": "Mediana",
  "display_order": 3
}
```

**Guardar:** `id` → `<OPC_TALLA_M>`

## 5. Opción `G`

```http
POST /api/v1/attribute-definitions/<ATR_TALLA_PANAL>/options
```

```json
{
  "code": "G",
  "name": "Grande",
  "display_order": 4
}
```

**Permiso que exige la URL:** `perm:product-catalog:attribute-definitions:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Crear una **opción** modifica la definición del atributo: exige `update`, no `create`.

**Por qué se hace así**

- Completa la lista de tallas para los demás pañales del Excel (Huggies, Winny, Content…).

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<OPC_TALLA_G>",
  "code": "G",
  "name": "Grande",
  "display_order": 4
}
```

**Guardar:** `id` → `<OPC_TALLA_G>`

## 6. Opción `XG`

```http
POST /api/v1/attribute-definitions/<ATR_TALLA_PANAL>/options
```

```json
{
  "code": "XG",
  "name": "Extra grande",
  "display_order": 5
}
```

**Permiso que exige la URL:** `perm:product-catalog:attribute-definitions:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Crear una **opción** modifica la definición del atributo: exige `update`, no `create`.

**Por qué se hace así**

- Completa la lista de tallas para los demás pañales del Excel (Huggies, Winny, Content…).

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<OPC_TALLA_XG>",
  "code": "XG",
  "name": "Extra grande",
  "display_order": 5
}
```

**Guardar:** `id` → `<OPC_TALLA_XG>`

## 7. Opción `XXG`

```http
POST /api/v1/attribute-definitions/<ATR_TALLA_PANAL>/options
```

```json
{
  "code": "XXG",
  "name": "Extra extra grande",
  "display_order": 6
}
```

**Permiso que exige la URL:** `perm:product-catalog:attribute-definitions:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Crear una **opción** modifica la definición del atributo: exige `update`, no `create`.

**Por qué se hace así**

- Completa la lista de tallas para los demás pañales del Excel (Huggies, Winny, Content…).

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<OPC_TALLA_XXG>",
  "code": "XXG",
  "name": "Extra extra grande",
  "display_order": 6
}
```

**Guardar:** `id` → `<OPC_TALLA_XXG>`

## 8. Opción `XXXG`

```http
POST /api/v1/attribute-definitions/<ATR_TALLA_PANAL>/options
```

```json
{
  "code": "XXXG",
  "name": "Triple extra grande",
  "display_order": 7
}
```

**Permiso que exige la URL:** `perm:product-catalog:attribute-definitions:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Crear una **opción** modifica la definición del atributo: exige `update`, no `create`.

**Por qué se hace así**

- Talla del producto de este ejercicio (`XXXG` en el nombre del Excel).

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<OPC_TALLA_XXXG>",
  "code": "XXXG",
  "name": "Triple extra grande",
  "display_order": 7
}
```

**Guardar:** `id` → `<OPC_TALLA_XXXG>`

## 9. Crear el atributo `ETAPA_PANAL` (entero)

```http
POST /api/v1/attribute-definitions
```

```json
{
  "code": "ETAPA_PANAL",
  "name": "Etapa del pañal",
  "description": "Etapa de crecimiento indicada por el fabricante.",
  "data_type": "INTEGER"
}
```

**Permiso que exige la URL:** `perm:product-catalog:attribute-definitions:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `create`

**Por qué se hace así**

- `INTEGER`: "ETAPA **6**" en el nombre del Excel.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<ATR_ETAPA_PANAL>",
  "code": "ETAPA_PANAL",
  "data_type": "INTEGER"
}
```

**Guardar:** `id` → `<ATR_ETAPA_PANAL>`

---

[← Paso anterior](03-crear-categorias.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](05-asociar-atributos-a-la-categoria.md)
