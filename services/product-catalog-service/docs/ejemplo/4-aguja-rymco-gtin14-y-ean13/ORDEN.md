# Ejercicio 4 — Aguja hipodérmica 18G x 1½" Rymco, caja x 100

[← Todos los ejercicios](../README.md)

**Qué enseña:** Tipos de identificador: un **GTIN-14** y un **EAN-13** que según la regla GS1 identifican niveles distintos (caja y unidad), y la **referencia del fabricante** como identificador `OTHER`. Además: **unidad nueva** (pulgada), producto **sin marca**, y dos **errores esperados** que protegen la calidad de los códigos.

**Filas del Excel:** ID 537 — detalle y decisiones en [00-datos-del-excel.md](00-datos-del-excel.md).

Antes de empezar revise los [requisitos comunes](../README.md#antes-de-empezar).

**Usuarios:** ejecútelo con `admin.test`. Qué puede hacer cada usuario de prueba, qué permiso exige cada URL y ejemplos de uso con cada uno: [USUARIOS.md](USUARIOS.md).

## Orden de ejecución

Ejecute los archivos **en este orden**. Cada paso usa `id` guardados en pasos anteriores.

| Paso | Archivo | Qué hace | Llamadas | Depende de |
| --- | --- | --- | --- | --- |
| 00 | [00-datos-del-excel.md](00-datos-del-excel.md) | Leer: qué dice el Excel y cómo se interpreta | — | — |
| 01 | [01-consultar-datos-base.md](01-consultar-datos-base.md) | Obtener los `id` de la unidad, el empaque, los tipos de grupo y el fabricante (registrándolo si todavía no existe). | 8 | — |
| 02 | [02-crear-unidad-pulgada.md](02-crear-unidad-pulgada.md) | Poder expresar la longitud de la aguja (1½"). | 1 | — |
| 03 | [03-crear-categorias.md](03-crear-categorias.md) | Crear `DISPOSITIVOS_MEDICOS > AGUJAS_HIPODERMICAS`. | 2 | — |
| 04 | [04-crear-atributos.md](04-crear-atributos.md) | Calibre y longitud de la aguja. | 2 | 02 |
| 05 | [05-asociar-atributos-a-la-categoria.md](05-asociar-atributos-a-la-categoria.md) | Ambos obligatorios y filtrables. | 2 | 03, 04 |
| 06 | [06-crear-producto.md](06-crear-producto.md) | Registrar la aguja. | 1 | 01 |
| 07 | [07-clasificar-producto.md](07-clasificar-producto.md) | Asignar `AGUJAS_HIPODERMICAS`. | 1 | 03, 06 |
| 08 | [08-registrar-valores-y-presentaciones.md](08-registrar-valores-y-presentaciones.md) | Calibre 18, longitud 1.5 pulgadas; presentaciones unidad y caja x 100. | 4 | 01, 04, 06 |
| 09 | [09-registrar-identificadores.md](09-registrar-identificadores.md) | EAN-13 a la unidad, GTIN-14 a la caja y referencia del fabricante como `OTHER`. | 5 | 06, 08 |
| 10 | [10-crear-y-asignar-grupos.md](10-crear-y-asignar-grupos.md) | Importar los grupos útiles. | 9 | 01, 06 |
| 11 | [11-verificar-resultado.md](11-verificar-resultado.md) | Escanear ambos códigos y buscar por la referencia del fabricante. | 3 | — |

## Por qué este orden

1. **Datos base.** Unidades, empaques, tipos de grupo y fabricante ya existen; todo lo demás usa sus `id`.
2. **Catálogos antes del producto.** Unidad nueva, marca, categorías y atributos se crean antes, porque el producto y sus valores los referencian. Una referencia inexistente da `422 REFERENCE_NOT_FOUND`.
3. **Atributos → categoría.** El atributo se asocia a la categoría antes de registrar valores: un valor solo se acepta si alguna categoría del producto usa ese atributo (`422 ATTRIBUTE_NOT_APPLICABLE`).
4. **Producto → categoría → valores.** Por la misma razón, el producto se clasifica antes de registrar sus valores.
5. **Presentaciones → códigos de barras.** El código de barras se liga a una presentación, que debe existir antes.
6. **Grupos.** Son independientes del resto: pueden asignarse en cualquier momento después de crear el producto.
7. **Verificación al final.** Con todo cargado, el producto debe quedar `is_complete: true`.

## Lista de `id` que debe ir guardando

| Variable | Se obtiene en | Se usa en |
| --- | --- | --- |
| `<UND>` | 01 | 06 |
| `<BOX>` | 01 | 08 |
| `<GT_GROUP_1>` | 01 | 10 |
| `<GT_GROUP_2>` | 01 | 10 |
| `<GT_GROUP_4>` | 01 | 10 |
| `<PAIS_CO>` | 01 | — |
| `<FABRICANTE_RYMCO>` | 01 | 06 |
| `<PULG>` | 02 | 04 |
| `<CAT_DISPOSITIVOS_MEDICOS>` | 03 | — |
| `<CAT_AGUJAS>` | 03 | 05, 07 |
| `<ATR_CALIBRE_AGUJA>` | 04 | 05, 08 |
| `<ATR_LONGITUD_AGUJA>` | 04 | 05, 08 |
| `<CA_CALIBRE>` | 05 | — |
| `<CA_LONGITUD>` | 05 | — |
| `<PRODUCTO>` | 06 | 07, 08, 09, 10 |
| `<PC_AGUJAS>` | 07 | — |
| `<PRES_UNIDAD>` | 08 | 09 |
| `<PRES_CAJA_X100>` | 08 | 09 |
| `<ID_EAN13>` | 09 | — |
| `<ID_GTIN14>` | 09 | — |
| `<ID_REF_FABRICANTE>` | 09 | — |
| `<GRUPO1_0005>` | 10 | — |
| `<ASIG_GRUPO1>` | 10 | — |
| `<GRUPO2_0016>` | 10 | — |
| `<ASIG_GRUPO2>` | 10 | — |
| `<GRUPO4_0278>` | 10 | — |
| `<ASIG_GRUPO4>` | 10 | — |

Las variables con `—` no se usan más en este ejercicio, pero conviene guardarlas: son las que se necesitan para corregir o inactivar ese registro después.

## Resultado esperado

Al terminar el paso 11 ([11-verificar-resultado.md](11-verificar-resultado.md)) el producto queda como se describe allí.

[Empezar → paso 01](01-consultar-datos-base.md)
