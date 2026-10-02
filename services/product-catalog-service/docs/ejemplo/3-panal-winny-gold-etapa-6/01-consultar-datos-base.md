# Paso 01 de 12 — Consultar los datos base

Ejercicio 3 — Pañal Winny Gold etapa 6 XXXG, paquete x 30 · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](02-crear-marca.md)

**Objetivo:** Obtener los `id` de la unidad, el empaque, los tipos de grupo y el fabricante (registrándolo si todavía no existe).

**Deja guardado para los siguientes pasos:** `<UND>`, `<PACK>`, `<GT_GROUP_1>`, `<GT_GROUP_2>`, `<GT_GROUP_4>`, `<PAIS_CO>`, `<FABRICANTE_TECNOQUIMICAS>`

---

## 1. Consultar la unidad `UND`

```http
GET /api/v1/units-of-measure?code=UND
```

**Permiso que exige la URL:** `perm:product-catalog:units-of-measure:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:product-catalog:all:read`), `ventas.test` (por `perm:product-catalog:all:read`), `inventario.test` (por `perm:product-catalog:all:read`), `reportes.test` (por `perm:product-catalog:units-of-measure:read`), `consulta.test` (por `perm:product-catalog:units-of-measure:read`)

**Por qué se hace así**

- El pañal se cuenta por unidades enteras: la unidad base es `UND`.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "id": "<UND>",
      "code": "UND",
      "name": "Unidad",
      "measurement_type": "UNIT",
      "allows_decimals": false
    }
  ],
  "total_records": 1
}
```

**Guardar:** `items[0].id` → `<UND>`

## 2. Consultar el tipo de empaque `PACK`

```http
GET /api/v1/packaging-types?code=PACK
```

**Permiso que exige la URL:** `perm:product-catalog:packaging-types:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:product-catalog:all:read`), `ventas.test` (por `perm:product-catalog:all:read`), `inventario.test` (por `perm:product-catalog:all:read`), `reportes.test` (por `perm:product-catalog:packaging-types:read`), `consulta.test` (por `perm:product-catalog:packaging-types:read`)

**Por qué se hace así**

- `Unidad Medida = PAQUETE` es un empaque: en el catálogo es `PACK`.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "id": "<PACK>",
      "code": "PACK",
      "name": "Paquete"
    }
  ],
  "total_records": 1
}
```

**Guardar:** `items[0].id` → `<PACK>`

## 3. Consultar el tipo de grupo `GROUP_1`

```http
GET /api/v1/group-types?code=GROUP_1
```

**Permiso que exige la URL:** `perm:product-catalog:group-types:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:product-catalog:all:read`), `ventas.test` (por `perm:product-catalog:all:read`), `inventario.test` (por `perm:product-catalog:all:read`), `reportes.test` (por `perm:product-catalog:group-types:read`), `consulta.test` (por `perm:product-catalog:group-types:read`)

**Por qué se hace así**

- La columna `Grupo 1` del Excel se guarda en el tipo de grupo `GROUP_1`, que la carga inicial ya creó. Se necesita su `id` para crear y consultar sus grupos.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "id": "<GT_GROUP_1>",
      "code": "GROUP_1",
      "allows_multiple": false
    }
  ],
  "total_records": 1
}
```

**Guardar:** `items[0].id` → `<GT_GROUP_1>`

## 4. Consultar el tipo de grupo `GROUP_2`

```http
GET /api/v1/group-types?code=GROUP_2
```

**Permiso que exige la URL:** `perm:product-catalog:group-types:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:product-catalog:all:read`), `ventas.test` (por `perm:product-catalog:all:read`), `inventario.test` (por `perm:product-catalog:all:read`), `reportes.test` (por `perm:product-catalog:group-types:read`), `consulta.test` (por `perm:product-catalog:group-types:read`)

**Por qué se hace así**

- La columna `Grupo 2` del Excel se guarda en el tipo de grupo `GROUP_2`, que la carga inicial ya creó. Se necesita su `id` para crear y consultar sus grupos.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "id": "<GT_GROUP_2>",
      "code": "GROUP_2",
      "allows_multiple": false
    }
  ],
  "total_records": 1
}
```

**Guardar:** `items[0].id` → `<GT_GROUP_2>`

## 5. Consultar el tipo de grupo `GROUP_4`

```http
GET /api/v1/group-types?code=GROUP_4
```

**Permiso que exige la URL:** `perm:product-catalog:group-types:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:product-catalog:all:read`), `ventas.test` (por `perm:product-catalog:all:read`), `inventario.test` (por `perm:product-catalog:all:read`), `reportes.test` (por `perm:product-catalog:group-types:read`), `consulta.test` (por `perm:product-catalog:group-types:read`)

**Por qué se hace así**

- La columna `Grupo 4` del Excel se guarda en el tipo de grupo `GROUP_4`, que la carga inicial ya creó. Se necesita su `id` para crear y consultar sus grupos.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "id": "<GT_GROUP_4>",
      "code": "GROUP_4",
      "allows_multiple": false
    }
  ],
  "total_records": 1
}
```

**Guardar:** `items[0].id` → `<GT_GROUP_4>`

## 6. Buscar el fabricante Tecnoquímicas en Party Identity Service

> **Otro servicio:** esta llamada va a **Party Identity Service**, no al catálogo.

```http
GET http://localhost:8002/organization-identities?search=TECNOQUIMICAS
```

**Permiso que exige la URL:** `perm:party-identity:organization_identities:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:party-identity:organization_identities:read`), `ventas.test` (por `perm:party-identity:organization_identities:read`), `reportes.test` (por `perm:party-identity:organization_identities:read`), `consulta.test` (por `perm:party-identity:organization_identities:read`)
- ❌ **No pueden (responde `403`):** `inventario.test` — no tiene ningún permiso sobre `party-identity`

**Por qué se hace así**

- El catálogo no guarda fabricantes: solo guarda el `id` de la organización registrada en Party Identity Service (puerto `8002`). Por eso esta consulta va a otro servicio.
- `search` busca parcialmente en la razón social, el nombre comercial y el número de identificación.
- Al crear el producto, el catálogo vuelve a preguntar a Party Identity si esa organización existe; si no existe responde `422 MANUFACTURER_NOT_FOUND`.

**Respuesta esperada — `200 OK`** (abreviada, en una base donde el fabricante todavía no existe)

```json
{
  "items": [],
  "page": 1,
  "page_size": 20,
  "total_records": 0,
  "total_pages": 0
}
```

**Si `items` trae la organización:** guarde `items[0].id` → `<FABRICANTE_TECNOQUIMICAS>` y **salte** las llamadas 2 y 3. Si trae varias, elija la correcta por `legal_name` e `identification_number`.

**Si viene vacío** (como arriba): el fabricante no está registrado; haga las llamadas 2 y 3 para crearlo.

## 7. Consultar el país Colombia en Geography Service (solo si el fabricante no existe)

> **Otro servicio:** esta llamada va a **Geography Service**, no al catálogo.

> **Solo si la búsqueda anterior devolvió `"items": []`.** Si el fabricante ya existía, omita esta llamada y la siguiente.

```http
GET http://localhost:8000/global-countries?iso2_code=CO
```

**Permiso que exige la URL:** `perm:geography:global_countries:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:geography:all:read`), `ventas.test` (por `perm:geography:all:read`), `inventario.test` (por `perm:geography:all:read`), `reportes.test` (por `perm:geography:global_countries:read`), `consulta.test` (por `perm:geography:global_countries:read`)

**Por qué se hace así**

- Party Identity exige el `country_id` del país que emitió la identificación; los países los administra **Geography Service** (puerto `8000`).
- Se filtra por `iso2_code` (código ISO de 2 letras), que es fijo, en vez de por nombre.
- En su entorno actual el `id` de Colombia es `cf160c2d-b6de-4ef5-9257-a0a8539058d9`; se consulta igual porque en otra base puede cambiar.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "id": "<PAIS_CO>",
      "iso2_code": "CO",
      "iso3_code": "COL",
      "name": "Colombia",
      "phone_prefix": "+57",
      "status": "ACTIVE"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_records": 1,
  "total_pages": 1
}
```

**Guardar:** `items[0].id` → `<PAIS_CO>`

## 8. Crear el fabricante Tecnoquímicas (solo si no existe)

> **Otro servicio:** esta llamada va a **Party Identity Service**, no al catálogo.

> **Solo si la búsqueda del fabricante devolvió `"items": []`.**

```http
POST http://localhost:8002/organization-identities
```

```json
{
  "country_id": "<PAIS_CO>",
  "identification_type": "NIT",
  "identification_number": "<DATO_NIT_TECNOQUIMICAS>",
  "legal_name": "<DATO_RAZON_SOCIAL_TECNOQUIMICAS>",
  "trade_name": "Tecnoquímicas",
  "registration_status": "ACTIVE"
}
```

**Permiso que exige la URL:** `perm:party-identity:organization_identities:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:create`)
- ❌ **No pueden (responde `403`):** `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` — sobre `party-identity` solo tienen `read`; les falta `create`; `inventario.test` — no tiene ningún permiso sobre `party-identity`

**Por qué se hace así**

- `<DATO_NIT_TECNOQUIMICAS>` y `<DATO_RAZON_SOCIAL_TECNOQUIMICAS>` **no salen del Excel**: son datos legales reales de la empresa. Tómelos del RUT del proveedor, de una factura suya o del registro mercantil (RUES). No invente un NIT: el registro es global y lo usarán todas las empresas.
- `identification_type: NIT` es la **sigla** del documento. Su entorno tiene una regla activa para Colombia que exige el formato `^[A-Z0-9]{4,11}-[0-9]$`: número, **guion** y dígito de verificación (ejemplo `900123456-7`). Si no lo cumple responde `422` "El número de identificación no cumple ninguna regla activa para la sigla indicada".
- `legal_name` es la razón social exacta (con `S.A.S.`, `S.A.`, etc.); `trade_name`, el nombre por el que se conoce.
- `registration_status: ACTIVE` igual que las organizaciones ya registradas. `organization_type` (p. ej. `SAS`) y `website` son opcionales: se omiten si no se conocen.
- Si esa combinación país + tipo + número ya existe responde `409`: vuelva a buscar por el NIT (`?search=<DATO_NIT_TECNOQUIMICAS>`) y use ese `id`.
- El usuario necesita el permiso `perm:party-identity:organization_identities:create` (o `perm:party-identity:all:all`).

**Respuesta esperada — `201 Created`** (abreviada)

```json
{
  "id": "<FABRICANTE_TECNOQUIMICAS>",
  "country_id": "<PAIS_CO>",
  "identification_type": "NIT",
  "identification_number": "<DATO_NIT_TECNOQUIMICAS>",
  "legal_name": "<DATO_RAZON_SOCIAL_TECNOQUIMICAS>",
  "trade_name": "Tecnoquímicas",
  "organization_type": null,
  "registration_status": "ACTIVE",
  "website": null,
  "version": 1
}
```

**Guardar:** `id` → `<FABRICANTE_TECNOQUIMICAS>`

---

[Orden del ejercicio](ORDEN.md) · [Paso siguiente →](02-crear-marca.md)
