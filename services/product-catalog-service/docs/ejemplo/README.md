# Ejemplos de carga con datos reales del Excel

Cinco ejercicios completos para crear productos en Product Catalog Service a partir de filas reales
de `docs/CAMPOS PRODUCTOS.xlsx` (16 889 productos, 143 columnas).

Cada carpeta es un ejercicio **independiente**:

- `ORDEN.md`: el orden en que se ejecutan los pasos, por qué va ese orden y la lista de `id` que se
  van guardando.
- `00-datos-del-excel.md`: qué dice la fila del Excel y qué se decidió con cada dato.
- `01-…md`, `02-…md`, …: un archivo por paso. Por cada llamada a la API se indica el endpoint, el
  JSON, **qué permiso exige y qué usuarios pueden ejecutarla**, **por qué se hace así** y la
  respuesta esperada.
- `USUARIOS.md`: qué puede hacer cada usuario de prueba en ese ejercicio, la tabla de permisos por
  URL y ejemplos de uso con los usuarios (llamadas permitidas y rechazadas).

Todos los JSON, respuestas y permisos los valida la prueba `tests/examples/` ejecutando los
ejercicios contra la API: cada uno por separado en una base nueva y los cinco seguidos en la misma
base, en orden normal e inverso. La mayor parte de estos documentos la genera esa misma prueba
(`PRODUCT_CATALOG_EXAMPLES_WRITE=1 pytest tests/examples`); solo este `README.md` y
`mapeo-campos-excel.md` se escriben a mano.

## Los cinco ejercicios

| Carpeta | Fila(s) del Excel | Qué enseña |
| --- | --- | --- |
| [1-acetaminofen-adorem-caja-x100](1-acetaminofen-adorem-caja-x100/ORDEN.md) | ID 45 · Acetaminofén (Adorem) 500 mg caja x 100 | Marca comercial escondida en el nombre, unidad nueva (`MG`), atributos `TEXT`, `DECIMAL` y `OPTION`, presentación base + caja con factor, dos EAN |
| [2-leche-nan-1-optipro-tres-latas](2-leche-nan-1-optipro-tres-latas/ORDEN.md) | IDs 7334, 6138, 7333 · NAN 1 Optipro lata 400/900/1100 g | **Tres filas = un producto** con tres presentaciones, gramo como unidad base, atributos `INTEGER` y `BOOLEAN`, grupos que no se importan |
| [3-panal-winny-gold-etapa-6](3-panal-winny-gold-etapa-6/ORDEN.md) | ID 17747 · Winny Gold etapa 6 XXXG paquete x 30 | Dato que solo está en el nombre (talla) → atributo `OPTION` filtrable, búsqueda por atributos |
| [4-aguja-rymco-gtin14-y-ean13](4-aguja-rymco-gtin14-y-ean13/ORDEN.md) | ID 537 · Aguja 18G x 1½" caja x 100 | GTIN-14 vs EAN-13 (caja y unidad), referencia del fabricante como `OTHER`, producto sin marca, unidad nueva (`PULG`), errores de códigos |
| [5-cepillo-colgate-inactivo](5-cepillo-colgate-inactivo/ORDEN.md) | ID 26396 · Cepillo Colgate infantil pack x 2 (`Estado = I`) | Código interno que no es código de barras, imagen del producto, inactivación y qué pasa con un producto inactivo |

Se recomienda hacerlos en orden (del 1 al 5), porque las explicaciones generales aparecen la primera
vez que se usa algo. Pero cualquiera se puede ejecutar solo.

Para saber en qué servicio va cada columna del Excel, vea [mapeo-campos-excel.md](mapeo-campos-excel.md).

Para saber con qué usuario ejecutar cada URL, vea [usuarios-y-permisos.md](usuarios-y-permisos.md).
Resumen: **`admin.test` puede hacer todos los ejercicios completos**; `supervisor.test` puede todo
menos inactivar (paso 12 del ejercicio 5); los demás usuarios de prueba solo pueden consultar.

## Antes de empezar

1. **Servicios levantados:** Product Catalog Service en `http://localhost:8003`, Party Identity
   Service en `http://localhost:8002` y Keycloak en `http://localhost:8081`.
2. **Carga inicial ejecutada** (una sola vez por base de datos):

   ```bash
   python -m product_catalog_service.seed load
   ```

   Crea las unidades (`UND`, `KG`, `G`, `LT`, `ML`, `M`, `CM`, `M2`), los tipos de empaque (`BOX`,
   `BOTTLE`, `TUBE`, `BAG`, `PACK`, `CAN`, `JAR`, `ENVELOPE`, `ROLL`, `BLISTER`) y los tipos de grupo
   `GROUP_1` a `GROUP_15`. Los ejercicios los **consultan**; no los crean.

3. **Token:** todas las llamadas llevan el encabezado

   ```http
   Authorization: Bearer <TOKEN>
   ```

   Se puede obtener con `python services/get_token.py admin` (o sin argumento, con un menú para elegir
   el usuario); la contraseña la toma de `KEYCLOAK_TEST_USER_PASSWORD`. Para otras formas vea
   [usuarios-y-permisos.md](usuarios-y-permisos.md#cómo-obtener-el-token-de-cada-usuario). El usuario debe tener
   `perm:product-catalog:all:all`, lectura y creación de organizaciones en Party Identity
   (`perm:party-identity:organization_identities:read` y `:create`) y lectura de países en Geography
   (`perm:geography:global_countries:read`). El usuario de pruebas `admin.test` ya los tiene.
   En los archivos de cada paso el encabezado se omite para acortar.

4. **Fabricantes en Party Identity:** el paso 01 de cada ejercicio busca su fabricante (Siegfried,
   Nestlé, Tecnoquímicas, Rymco, Colgate-Palmolive). Si no existe, el mismo paso explica cómo
   crearlo: se consulta el país en Geography Service (`http://localhost:8000`) y se registra la
   organización con su **NIT y razón social reales** (`<DATO_NIT_…>`, `<DATO_RAZON_SOCIAL_…>`), que
   no vienen en el Excel. Si todavía no tiene esos datos, cree el producto **sin**
   `manufacturer_organization_id` (es opcional) y asígnelo después con `PUT /api/v1/products/{id}`.

## Cómo leer los pasos

- **Variables `<NOMBRE>`**: un texto como `<PRODUCTO>` o `<CAT_LECHES>` se reemplaza por el `id` real
  que devolvió una llamada anterior. Cada llamada dice qué guardar (**Guardar:** `id` → `<PRODUCTO>`)
  y cada `ORDEN.md` tiene la tabla completa de variables. Las que empiezan por `<DATO_…>` no son
  `id`: son datos que usted debe conseguir (por ejemplo, el NIT real de un fabricante).
- **Respuestas abreviadas**: solo se muestran los campos que interesan en ese paso. Los campos de
  auditoría (`created_at`, `created_by`, …) y el `trace_id` se omiten.
- **Decimales**: el servicio devuelve los decimales como texto con 8 decimales
  (`"base_quantity": "100.00000000"`). En las solicitudes se pueden enviar como número (`100`).
- **Errores esperados**: algunos pasos hacen a propósito una llamada que falla, para mostrar una
  regla. Están marcados como *Error esperado* y su respuesta es un `4xx`.
- **Códigos que ya existen**: si un `POST` de una unidad, marca, categoría o atributo responde
  `409 DUPLICATE_CODE`, ese registro ya existe en su base (por ejemplo, de una prueba anterior).
  Consúltelo con `GET …?code=<código>` y use su `id`. Los grupos se consultan siempre antes de
  crearlos, porque los comparten muchos productos (los ejercicios 4 y 5 usan los mismos grupos
  `0005` y `0016`).
- **Base limpia recomendada**: si ya cargó ejemplos anteriores en la misma base, pueden existir
  atributos con el mismo código y otras opciones. Lo más simple es practicar en una base nueva.

## Ejemplo con curl

```bash
TOKEN=$(python services/get_token.py admin)

curl -X POST http://localhost:8003/api/v1/brands \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"code": "ADOREM", "name": "Adorem", "description": "Marca comercial de acetaminofén de Siegfried."}'
```

## Qué no cubren estos ejercicios

- **Primer uso** (`POST /products/{id}/first-use`): lo llama el servicio que adopta el producto
  (Commercial Relationship), no quien carga el catálogo. Ver [../api/10-primer-uso.md](../api/10-primer-uso.md).
- **Datos de empresa** (precios, stock, código interno, impuestos): no pertenecen al catálogo global.
  Ver [mapeo-campos-excel.md](mapeo-campos-excel.md).

Referencia de cada ruta: [../api/](../api/README.md). Conceptos generales: [../api-guide.md](../api-guide.md).
