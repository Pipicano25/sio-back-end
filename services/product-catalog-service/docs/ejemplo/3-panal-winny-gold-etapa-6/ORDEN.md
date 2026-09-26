# Ejercicio 3 — Pañal Winny Gold etapa 6 XXXG, paquete x 30

[← Todos los ejercicios](../README.md)

**Qué enseña:** Un dato que en el Excel solo está **dentro del nombre** (la talla `XXXG`) se convierte en un **atributo de lista (`OPTION`) filtrable**, con todas sus opciones ordenadas. Se termina **buscando productos por atributos**.

**Filas del Excel:** ID 17747 — detalle y decisiones en [00-datos-del-excel.md](00-datos-del-excel.md).

Antes de empezar revise los [requisitos comunes](../README.md#antes-de-empezar).

**Usuarios:** ejecútelo con `admin.test`. Qué puede hacer cada usuario de prueba, qué permiso exige cada URL y ejemplos de uso con cada uno: [USUARIOS.md](USUARIOS.md).

## Orden de ejecución

Ejecute los archivos **en este orden**. Cada paso usa `id` guardados en pasos anteriores.

| Paso | Archivo | Qué hace | Llamadas | Depende de |
| --- | --- | --- | --- | --- |
| 00 | [00-datos-del-excel.md](00-datos-del-excel.md) | Leer: qué dice el Excel y cómo se interpreta | — | — |
| 01 | [01-consultar-datos-base.md](01-consultar-datos-base.md) | Obtener los `id` de la unidad, el empaque, los tipos de grupo y el fabricante (registrándolo si todavía no existe). | 8 | — |
| 02 | [02-crear-marca.md](02-crear-marca.md) | Registrar la marca comercial. | 1 | — |
| 03 | [03-crear-categorias.md](03-crear-categorias.md) | Crear `CUIDADO_BEBE > PANALES_BEBE`. | 2 | — |
| 04 | [04-crear-atributos.md](04-crear-atributos.md) | Definir la talla como lista cerrada y la etapa como número. | 9 | — |
| 05 | [05-asociar-atributos-a-la-categoria.md](05-asociar-atributos-a-la-categoria.md) | La talla obligatoria y filtrable; la etapa opcional y filtrable. | 2 | 03, 04 |
| 06 | [06-crear-producto.md](06-crear-producto.md) | Registrar el pañal. | 1 | 01, 02 |
| 07 | [07-clasificar-producto.md](07-clasificar-producto.md) | Asignar `PANALES_BEBE`. | 1 | 03, 06 |
| 08 | [08-registrar-valores-de-atributos.md](08-registrar-valores-de-atributos.md) | Talla XXXG y etapa 6. | 2 | 04, 06 |
| 09 | [09-crear-presentacion.md](09-crear-presentacion.md) | Paquete x 30 pañales. | 1 | 01, 06 |
| 10 | [10-registrar-codigos-de-barras.md](10-registrar-codigos-de-barras.md) | Los dos EAN del paquete. | 2 | 06, 09 |
| 11 | [11-crear-y-asignar-grupos.md](11-crear-y-asignar-grupos.md) | Importar los grupos útiles. | 9 | 01, 06 |
| 12 | [12-verificar-y-buscar-por-atributos.md](12-verificar-y-buscar-por-atributos.md) | Comprobar el producto y usar los filtros por atributo. | 4 | 03, 06 |

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
| `<PACK>` | 01 | 09 |
| `<GT_GROUP_1>` | 01 | 11 |
| `<GT_GROUP_2>` | 01 | 11 |
| `<GT_GROUP_4>` | 01 | 11 |
| `<PAIS_CO>` | 01 | — |
| `<FABRICANTE_TECNOQUIMICAS>` | 01 | 06 |
| `<MARCA_WINNY>` | 02 | 06 |
| `<CAT_CUIDADO_BEBE>` | 03 | — |
| `<CAT_PANALES_BEBE>` | 03 | 05, 07, 12 |
| `<ATR_TALLA_PANAL>` | 04 | 05, 08 |
| `<OPC_TALLA_RN>` | 04 | — |
| `<OPC_TALLA_P>` | 04 | — |
| `<OPC_TALLA_M>` | 04 | — |
| `<OPC_TALLA_G>` | 04 | — |
| `<OPC_TALLA_XG>` | 04 | — |
| `<OPC_TALLA_XXG>` | 04 | — |
| `<OPC_TALLA_XXXG>` | 04 | 08 |
| `<ATR_ETAPA_PANAL>` | 04 | 05, 08 |
| `<CA_TALLA_PANAL>` | 05 | — |
| `<CA_ETAPA_PANAL>` | 05 | — |
| `<PRODUCTO>` | 06 | 07, 08, 09, 10, 11, 12 |
| `<PC_PANALES>` | 07 | — |
| `<PRES_PAQUETE_X30>` | 09 | 10 |
| `<ID_EAN_1>` | 10 | — |
| `<ID_EAN_2>` | 10 | — |
| `<GRUPO1_0113>` | 11 | — |
| `<ASIG_GRUPO1>` | 11 | — |
| `<GRUPO2_0691>` | 11 | — |
| `<ASIG_GRUPO2>` | 11 | — |
| `<GRUPO4_0125>` | 11 | — |
| `<ASIG_GRUPO4>` | 11 | — |

Las variables con `—` no se usan más en este ejercicio, pero conviene guardarlas: son las que se necesitan para corregir o inactivar ese registro después.

## Resultado esperado

Al terminar el paso 12 ([12-verificar-y-buscar-por-atributos.md](12-verificar-y-buscar-por-atributos.md)) el producto queda como se describe allí.

[Empezar → paso 01](01-consultar-datos-base.md)
