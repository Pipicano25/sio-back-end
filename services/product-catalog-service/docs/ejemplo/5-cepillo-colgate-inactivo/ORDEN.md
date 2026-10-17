# Ejercicio 5 — Cepillo Colgate infantil pack x 2 (producto inactivo)

[← Todos los ejercicios](../README.md)

**Qué enseña:** Un producto con `Estado = I` en el Excel: se carga **completo** y al final se **inactiva**. En el camino: un "código de barras" que en realidad es el **código interno** (no se registra), una **imagen** del producto (activo digital) y qué se puede y qué no se puede hacer sobre un producto inactivo.

**Filas del Excel:** ID 26396 — detalle y decisiones en [00-datos-del-excel.md](00-datos-del-excel.md).

Antes de empezar revise los [requisitos comunes](../README.md#antes-de-empezar).

**Usuarios:** ejecútelo con `admin.test`. Qué puede hacer cada usuario de prueba, qué permiso exige cada URL y ejemplos de uso con cada uno: [USUARIOS.md](USUARIOS.md).

## Orden de ejecución

Ejecute los archivos **en este orden**. Cada paso usa `id` guardados en pasos anteriores.

| Paso | Archivo | Qué hace | Llamadas | Depende de |
| --- | --- | --- | --- | --- |
| 00 | [00-datos-del-excel.md](00-datos-del-excel.md) | Leer: qué dice el Excel y cómo se interpreta | — | — |
| 01 | [01-consultar-datos-base.md](01-consultar-datos-base.md) | Obtener los `id` de la unidad, el empaque, los tipos de grupo y el fabricante (registrándolo si todavía no existe). | 8 | — |
| 02 | [02-crear-marca.md](02-crear-marca.md) | Registrar la marca comercial. | 1 | — |
| 03 | [03-crear-categorias.md](03-crear-categorias.md) | Crear `CUIDADO_ORAL > CEPILLOS_DENTALES`. | 2 | — |
| 04 | [04-crear-atributos.md](04-crear-atributos.md) | Dureza de las cerdas (lista) y rango de edad (texto). | 6 | — |
| 05 | [05-asociar-atributos-a-la-categoria.md](05-asociar-atributos-a-la-categoria.md) | Dureza obligatoria y filtrable; rango de edad opcional. | 2 | 03, 04 |
| 06 | [06-crear-producto.md](06-crear-producto.md) | Registrar el cepillo **activo**, aunque el Excel diga `I`. | 1 | 01, 02 |
| 07 | [07-clasificar-y-registrar-atributos.md](07-clasificar-y-registrar-atributos.md) | Asignar la categoría y dar valor a los atributos. | 3 | 03, 04, 06 |
| 08 | [08-crear-presentacion.md](08-crear-presentacion.md) | Pack x 2 cepillos. | 1 | 01, 06 |
| 09 | [09-codigo-interno-no-es-codigo-de-barras.md](09-codigo-interno-no-es-codigo-de-barras.md) | Entender por qué el "código de barras" del Excel no va al catálogo. | 2 | 06, 08 |
| 10 | [10-agregar-imagen.md](10-agregar-imagen.md) | Registrar un activo digital (foto). | 1 | 06 |
| 11 | [11-crear-y-asignar-grupos.md](11-crear-y-asignar-grupos.md) | Conservar la agrupación del sistema anterior. | 9 | 01, 06 |
| 12 | [12-inactivar-producto.md](12-inactivar-producto.md) | Comprobar que quedó completo y luego inactivarlo. | 2 | 06 |
| 13 | [13-verificar-producto-inactivo.md](13-verificar-producto-inactivo.md) | Ver qué se puede y qué no se puede hacer con un producto inactivo. | 3 | 06 |
| 14 | [14-consultas-por-lotes.md](14-consultas-por-lotes.md) | Ver el resumen del catálogo de un lote de productos y buscar productos por marca, para consumidores como el servicio de consultas consolidadas. | 3 | 02, 06 |

## Por qué este orden

1. **Datos base.** Unidades, empaques, tipos de grupo y fabricante ya existen; todo lo demás usa sus `id`.
2. **Catálogos antes del producto.** Unidad nueva, marca, categorías y atributos se crean antes, porque el producto y sus valores los referencian. Una referencia inexistente da `422 REFERENCE_NOT_FOUND`.
3. **Atributos → categoría.** El atributo se asocia a la categoría antes de registrar valores: un valor solo se acepta si alguna categoría del producto usa ese atributo (`422 ATTRIBUTE_NOT_APPLICABLE`).
4. **Producto → categoría → valores.** Por la misma razón, el producto se clasifica antes de registrar sus valores.
5. **Presentaciones → códigos de barras.** El código de barras se liga a una presentación, que debe existir antes.
6. **Grupos.** Son independientes del resto: pueden asignarse en cualquier momento después de crear el producto.
7. **Verificación al final.** Con todo cargado, el producto debe quedar `is_complete: true`.
8. **Inactivar al final.** Sobre un producto inactivo no se pueden agregar elementos (`422 PRODUCT_INACTIVE`); por eso se carga completo y se inactiva de último.

## Lista de `id` que debe ir guardando

| Variable | Se obtiene en | Se usa en |
| --- | --- | --- |
| `<UND>` | 01 | 06 |
| `<PACK>` | 01 | 08 |
| `<GT_GROUP_1>` | 01 | 11 |
| `<GT_GROUP_2>` | 01 | 11 |
| `<GT_GROUP_4>` | 01 | 11 |
| `<PAIS_CO>` | 01 | — |
| `<FABRICANTE_COLGATE>` | 01 | 06 |
| `<MARCA_COLGATE>` | 02 | 06, 14 |
| `<CAT_CUIDADO_ORAL>` | 03 | — |
| `<CAT_CEPILLOS>` | 03 | 05, 07 |
| `<ATR_DUREZA_CERDAS>` | 04 | 05, 07 |
| `<OPC_EXTRA_SUAVE>` | 04 | 07 |
| `<OPC_SUAVE>` | 04 | — |
| `<OPC_MEDIO>` | 04 | — |
| `<OPC_DURO>` | 04 | — |
| `<ATR_RANGO_EDAD>` | 04 | 05, 07 |
| `<CA_DUREZA>` | 05 | — |
| `<CA_RANGO_EDAD>` | 05 | — |
| `<PRODUCTO>` | 06 | 07, 08, 09, 10, 11, 12, 13, 14 |
| `<PC_CEPILLOS>` | 07 | — |
| `<PRES_PACK_X2>` | 08 | 09 |
| `<ACTIVO_IMAGEN>` | 10 | — |
| `<GRUPO1_0005>` | 11 | — |
| `<ASIG_GRUPO1>` | 11 | — |
| `<GRUPO2_0016>` | 11 | — |
| `<ASIG_GRUPO2>` | 11 | — |
| `<GRUPO4_0213>` | 11 | — |
| `<ASIG_GRUPO4>` | 11 | — |

Las variables con `—` no se usan más en este ejercicio, pero conviene guardarlas: son las que se necesitan para corregir o inactivar ese registro después.

## Resultado esperado

Al terminar el paso 14 ([14-consultas-por-lotes.md](14-consultas-por-lotes.md)) el producto queda como se describe allí.

[Empezar → paso 01](01-consultar-datos-base.md)
