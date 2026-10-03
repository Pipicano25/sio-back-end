# Paso 01 de 05 — Recorrer el árbol CIIU

Ejercicio 7 — Sectores económicos: árbol CIIU, catálogo propio y sectores de una organización · [Orden del ejercicio](ORDEN.md) · [Paso siguiente →](02-clasificacion-propia.md)

**Objetivo:** Obtener las secciones y bajar hasta una clase.

**Deja guardado para los siguientes pasos:** `<SECCION_A>`, `<CLASE_CAFE>`, `<CLASE_TIENDA>`

---

## 1. Listar las secciones CIIU (raíces del árbol)

```http
GET /api/v1/global-business-sectors?classification_system=CIIU_REV5_AC&level_root=true&page_size=5
```

**Permiso que exige la URL:** `perm:party-identity:global_business_sectors:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:party-identity:global_business_sectors:read`), `ventas.test` (por `perm:party-identity:global_business_sectors:read`), `reportes.test` (por `perm:party-identity:global_business_sectors:read`), `consulta.test` (por `perm:party-identity:global_business_sectors:read`)
- ❌ **No pueden (responde `403`):** `inventario.test` — no tiene ningún permiso sobre `party-identity`

**Por qué se hace así**

- `level_root=true` devuelve solo sectores sin padre: las 22 secciones de la CIIU Rev. 5 A.C.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "total_records": 22
}
```

## 2. Consultar la sección A

```http
GET /api/v1/global-business-sectors?classification_system=CIIU_REV5_AC&code=A
```

**Permiso que exige la URL:** `perm:party-identity:global_business_sectors:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:party-identity:global_business_sectors:read`), `ventas.test` (por `perm:party-identity:global_business_sectors:read`), `reportes.test` (por `perm:party-identity:global_business_sectors:read`), `consulta.test` (por `perm:party-identity:global_business_sectors:read`)
- ❌ **No pueden (responde `403`):** `inventario.test` — no tiene ningún permiso sobre `party-identity`

**Por qué se hace así**

- `classification_system` + `code` identifican un sector; el `id` cambia entre entornos, el código no.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "total_records": 1
}
```

**Guardar:** `items[0].id` → `<SECCION_A>`

## 3. Listar las divisiones de la sección A

```http
GET /api/v1/global-business-sectors?parent_sector_id=<SECCION_A>
```

**Permiso que exige la URL:** `perm:party-identity:global_business_sectors:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:party-identity:global_business_sectors:read`), `ventas.test` (por `perm:party-identity:global_business_sectors:read`), `reportes.test` (por `perm:party-identity:global_business_sectors:read`), `consulta.test` (por `perm:party-identity:global_business_sectors:read`)
- ❌ **No pueden (responde `403`):** `inventario.test` — no tiene ningún permiso sobre `party-identity`

**Por qué se hace así**

- Los hijos directos se filtran con `parent_sector_id`.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "total_records": 3
}
```

## 4. Consultar la clase 0123 (Cultivo de café)

```http
GET /api/v1/global-business-sectors?classification_system=CIIU_REV5_AC&code=0123
```

**Permiso que exige la URL:** `perm:party-identity:global_business_sectors:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:party-identity:global_business_sectors:read`), `ventas.test` (por `perm:party-identity:global_business_sectors:read`), `reportes.test` (por `perm:party-identity:global_business_sectors:read`), `consulta.test` (por `perm:party-identity:global_business_sectors:read`)
- ❌ **No pueden (responde `403`):** `inventario.test` — no tiene ningún permiso sobre `party-identity`

**Por qué se hace así**

- Se asignan **clases** (4 dígitos), el nivel más específico; el filtro `code` es exacto.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "total_records": 1
}
```

**Guardar:** `items[0].id` → `<CLASE_CAFE>`

## 5. Consultar la clase 4711 por texto

```http
GET /api/v1/global-business-sectors?classification_system=CIIU_REV5_AC&search=4711
```

**Permiso que exige la URL:** `perm:party-identity:global_business_sectors:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:party-identity:global_business_sectors:read`), `ventas.test` (por `perm:party-identity:global_business_sectors:read`), `reportes.test` (por `perm:party-identity:global_business_sectors:read`), `consulta.test` (por `perm:party-identity:global_business_sectors:read`)
- ❌ **No pueden (responde `403`):** `inventario.test` — no tiene ningún permiso sobre `party-identity`

**Por qué se hace así**

- `search` busca en el código o en el nombre.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "total_records": 1
}
```

**Guardar:** `items[0].id` → `<CLASE_TIENDA>`

## 6. Ver el detalle de la clase 0123

```http
GET /api/v1/global-business-sectors/<CLASE_CAFE>
```

**Permiso que exige la URL:** `perm:party-identity:global_business_sectors:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:party-identity:global_business_sectors:read`), `ventas.test` (por `perm:party-identity:global_business_sectors:read`), `reportes.test` (por `perm:party-identity:global_business_sectors:read`), `consulta.test` (por `perm:party-identity:global_business_sectors:read`)
- ❌ **No pueden (responde `403`):** `inventario.test` — no tiene ningún permiso sobre `party-identity`

**Por qué se hace así**

- Su padre es el grupo `012` (Cultivos agrícolas permanentes).

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "id": "<CLASE_CAFE>",
  "classification_system": "CIIU_REV5_AC",
  "code": "0123",
  "name": "Cultivo de café",
  "parent_sector_id": "<id generado>",
  "status": "ACTIVE",
  "version": 1
}
```

---

[Orden del ejercicio](ORDEN.md) · [Paso siguiente →](02-clasificacion-propia.md)
