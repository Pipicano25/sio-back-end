# Paso 05 de 13 — Crear las definiciones de atributo y sus opciones

Ejercicio 1 — Acetaminofén Adorem 500 mg, caja x 100 · [← Paso anterior](04-crear-categorias.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](06-asociar-atributos-a-la-categoria.md)

**Objetivo:** Definir los datos técnicos que describen al medicamento: principio activo, concentración y forma farmacéutica.

**Necesita (de pasos anteriores):** `<MG>` — pasos [02](02-crear-unidad-mg.md)

**Deja guardado para los siguientes pasos:** `<ATR_PRINCIPIO_ACTIVO>`, `<ATR_CONCENTRACION_MG>`, `<ATR_FORMA_FARMACEUTICA>`, `<OPC_TABLETA>`, `<OPC_CAPSULA>`, `<OPC_JARABE>`

---

## 1. Crear el atributo `PRINCIPIO_ACTIVO` (texto)

```http
POST /api/v1/attribute-definitions
```

```json
{
  "code": "PRINCIPIO_ACTIVO",
  "name": "Principio activo",
  "description": "Sustancia responsable del efecto del medicamento.",
  "data_type": "TEXT"
}
```

**Permiso que exige la URL:** `perm:product-catalog:attribute-definitions:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `create`

**Por qué se hace así**

- `TEXT` porque el principio activo es un nombre libre (acetaminofén, ibuprofeno, …).
- `description` es **obligatoria** en las definiciones de atributo.
- `data_type` no se puede cambiar después.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<ATR_PRINCIPIO_ACTIVO>",
  "code": "PRINCIPIO_ACTIVO",
  "name": "Principio activo",
  "data_type": "TEXT",
  "unit_of_measure_id": null,
  "status": "ACTIVE"
}
```

**Guardar:** `id` → `<ATR_PRINCIPIO_ACTIVO>`

## 2. Crear el atributo `CONCENTRACION_MG` (decimal en mg)

```http
POST /api/v1/attribute-definitions
```

```json
{
  "code": "CONCENTRACION_MG",
  "name": "Concentración (mg)",
  "description": "Cantidad de principio activo por unidad, en miligramos.",
  "data_type": "DECIMAL",
  "unit_of_measure_id": "<MG>"
}
```

**Permiso que exige la URL:** `perm:product-catalog:attribute-definitions:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `create`

**Por qué se hace así**

- `DECIMAL` porque es una cantidad que puede tener decimales.
- `unit_of_measure_id` fija la unidad (mg) para todos los productos: así el valor guardado es solo el número (`500`).
- Solo `INTEGER` y `DECIMAL` admiten unidad; en otro tipo responde `422 UNIT_NOT_ALLOWED_FOR_DATA_TYPE`.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<ATR_CONCENTRACION_MG>",
  "code": "CONCENTRACION_MG",
  "name": "Concentración (mg)",
  "data_type": "DECIMAL",
  "unit_of_measure_id": "<MG>",
  "status": "ACTIVE"
}
```

**Guardar:** `id` → `<ATR_CONCENTRACION_MG>`

## 3. Crear el atributo `FORMA_FARMACEUTICA` (lista de opciones)

```http
POST /api/v1/attribute-definitions
```

```json
{
  "code": "FORMA_FARMACEUTICA",
  "name": "Forma farmacéutica",
  "description": "Forma en que se presenta el medicamento.",
  "data_type": "OPTION"
}
```

**Permiso que exige la URL:** `perm:product-catalog:attribute-definitions:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `create`

**Por qué se hace así**

- `OPTION` porque los valores posibles son una lista cerrada (tableta, cápsula, jarabe, …). Con texto libre aparecerían variantes como "TAB", "tableta", "Tabletas" que no se pueden filtrar.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<ATR_FORMA_FARMACEUTICA>",
  "code": "FORMA_FARMACEUTICA",
  "name": "Forma farmacéutica",
  "data_type": "OPTION",
  "status": "ACTIVE"
}
```

**Guardar:** `id` → `<ATR_FORMA_FARMACEUTICA>`

## 4. Crear la opción `TABLETA`

```http
POST /api/v1/attribute-definitions/<ATR_FORMA_FARMACEUTICA>/options
```

```json
{
  "code": "TABLETA",
  "name": "Tableta",
  "display_order": 1
}
```

**Permiso que exige la URL:** `perm:product-catalog:attribute-definitions:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Crear una **opción** modifica la definición del atributo: exige `update`, no `create`.

**Por qué se hace así**

- Es la forma de este producto (`TABLETA` en el nombre del Excel).
- `display_order` ordena las opciones en las listas de selección.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<OPC_TABLETA>",
  "attribute_definition_id": "<ATR_FORMA_FARMACEUTICA>",
  "code": "TABLETA",
  "name": "Tableta",
  "display_order": 1,
  "status": "ACTIVE"
}
```

**Guardar:** `id` → `<OPC_TABLETA>`

## 5. Crear la opción `CAPSULA`

```http
POST /api/v1/attribute-definitions/<ATR_FORMA_FARMACEUTICA>/options
```

```json
{
  "code": "CAPSULA",
  "name": "Cápsula",
  "display_order": 2
}
```

**Permiso que exige la URL:** `perm:product-catalog:attribute-definitions:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Crear una **opción** modifica la definición del atributo: exige `update`, no `create`.

**Por qué se hace así**

- No la usa este producto, pero la necesitan otros medicamentos del Excel. Las opciones se definen una vez para toda la lista.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<OPC_CAPSULA>",
  "code": "CAPSULA",
  "name": "Cápsula",
  "display_order": 2
}
```

**Guardar:** `id` → `<OPC_CAPSULA>`

## 6. Crear la opción `JARABE`

```http
POST /api/v1/attribute-definitions/<ATR_FORMA_FARMACEUTICA>/options
```

```json
{
  "code": "JARABE",
  "name": "Jarabe",
  "display_order": 3
}
```

**Permiso que exige la URL:** `perm:product-catalog:attribute-definitions:update`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:update`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `inventario.test`, `reportes.test`, `consulta.test` — sobre `product-catalog` solo tienen `read`; les falta `update`
- ℹ️ Crear una **opción** modifica la definición del atributo: exige `update`, no `create`.

**Por qué se hace así**

- Igual que la anterior: completa la lista para otros productos.

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<OPC_JARABE>",
  "code": "JARABE",
  "name": "Jarabe",
  "display_order": 3
}
```

**Guardar:** `id` → `<OPC_JARABE>`

---

[← Paso anterior](04-crear-categorias.md) · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](06-asociar-atributos-a-la-categoria.md)
