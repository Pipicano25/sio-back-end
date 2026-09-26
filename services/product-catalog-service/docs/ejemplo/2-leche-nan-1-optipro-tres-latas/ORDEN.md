# Ejercicio 2 — Leche NAN 1 Optipro: tres filas del Excel, un solo producto

[← Todos los ejercicios](../README.md)

**Qué enseña:** Cómo **tres filas del Excel** (lata de 400 g, 900 g y 1100 g) se cargan como **un solo producto con tres presentaciones**, usando el **gramo** como unidad base. Además: atributos `INTEGER` y `BOOLEAN`, un código de barras por presentación y grupos del Excel que **no** se importan.

**Filas del Excel:** ID 7334, 6138 y 7333 — detalle y decisiones en [00-datos-del-excel.md](00-datos-del-excel.md).

Antes de empezar revise los [requisitos comunes](../README.md#antes-de-empezar).

**Usuarios:** ejecútelo con `admin.test`. Qué puede hacer cada usuario de prueba, qué permiso exige cada URL y ejemplos de uso con cada uno: [USUARIOS.md](USUARIOS.md).

## Orden de ejecución

Ejecute los archivos **en este orden**. Cada paso usa `id` guardados en pasos anteriores.

| Paso | Archivo | Qué hace | Llamadas | Depende de |
| --- | --- | --- | --- | --- |
| 00 | [00-datos-del-excel.md](00-datos-del-excel.md) | Leer: qué dice el Excel y cómo se interpreta | — | — |
| 01 | [01-consultar-datos-base.md](01-consultar-datos-base.md) | Obtener los `id` de la unidad, el empaque, los tipos de grupo y el fabricante (registrándolo si todavía no existe). | 8 | — |
| 02 | [02-crear-marca.md](02-crear-marca.md) | Registrar la marca comercial. | 1 | — |
| 03 | [03-crear-categorias.md](03-crear-categorias.md) | Crear `ALIMENTOS > LECHES`. | 2 | — |
| 04 | [04-crear-atributos.md](04-crear-atributos.md) | Definir la etapa de la fórmula y si es fórmula infantil. | 2 | — |
| 05 | [05-asociar-atributos-a-la-categoria.md](05-asociar-atributos-a-la-categoria.md) | Indicar cómo usa `LECHES` cada atributo. | 2 | 03, 04 |
| 06 | [06-crear-producto.md](06-crear-producto.md) | Registrar un único producto con el gramo como unidad base. | 1 | 01, 02 |
| 07 | [07-clasificar-producto.md](07-clasificar-producto.md) | Asignar la categoría `LECHES`. | 1 | 03, 06 |
| 08 | [08-registrar-valores-de-atributos.md](08-registrar-valores-de-atributos.md) | Etapa 1 y fórmula infantil = sí. | 2 | 04, 06 |
| 09 | [09-crear-presentaciones.md](09-crear-presentaciones.md) | Una presentación por cada fila del Excel. | 3 | 01, 06 |
| 10 | [10-registrar-codigos-de-barras.md](10-registrar-codigos-de-barras.md) | Cada EAN del Excel va a la presentación de su fila. | 3 | 06, 09 |
| 11 | [11-crear-y-asignar-grupos.md](11-crear-y-asignar-grupos.md) | Importar solo los grupos que agrupan algo. | 9 | 01, 06 |
| 12 | [12-verificar-resultado.md](12-verificar-resultado.md) | Comprobar que cada código lleva a su lata y que el producto quedó elegible. | 3 | 06 |

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
| `<G>` | 01 | 06 |
| `<CAN>` | 01 | 09 |
| `<GT_GROUP_1>` | 01 | 11 |
| `<GT_GROUP_2>` | 01 | 11 |
| `<GT_GROUP_4>` | 01 | 11 |
| `<PAIS_CO>` | 01 | — |
| `<FABRICANTE_NESTLE>` | 01 | 06 |
| `<MARCA_NAN>` | 02 | 06 |
| `<CAT_ALIMENTOS>` | 03 | — |
| `<CAT_LECHES>` | 03 | 05, 07 |
| `<ATR_ETAPA_FORMULA>` | 04 | 05, 08 |
| `<ATR_FORMULA_INFANTIL>` | 04 | 05, 08 |
| `<CA_FORMULA_INFANTIL>` | 05 | — |
| `<CA_ETAPA_FORMULA>` | 05 | — |
| `<PRODUCTO>` | 06 | 07, 08, 09, 10, 11, 12 |
| `<PC_LECHES>` | 07 | — |
| `<PRES_LATA_400G>` | 09 | 10 |
| `<PRES_LATA_900G>` | 09 | 10 |
| `<PRES_LATA_1100G>` | 09 | 10 |
| `<ID_EAN_400G>` | 10 | — |
| `<ID_EAN_900G>` | 10 | — |
| `<ID_EAN_1100G>` | 10 | — |
| `<GRUPO1_0687>` | 11 | — |
| `<ASIG_GRUPO1>` | 11 | — |
| `<GRUPO2_0689>` | 11 | — |
| `<ASIG_GRUPO2>` | 11 | — |
| `<GRUPO4_0336>` | 11 | — |
| `<ASIG_GRUPO4>` | 11 | — |

Las variables con `—` no se usan más en este ejercicio, pero conviene guardarlas: son las que se necesitan para corregir o inactivar ese registro después.

## Resultado esperado

Al terminar el paso 12 ([12-verificar-resultado.md](12-verificar-resultado.md)) el producto queda como se describe allí.

[Empezar → paso 01](01-consultar-datos-base.md)
