# Ejercicio 1 — Acetaminofén Adorem 500 mg, caja x 100

[← Todos los ejercicios](../README.md)

**Qué enseña:** Medicamento ético con **marca comercial**, **unidad de medida nueva** (`MG`), atributos de tres tipos (`TEXT`, `DECIMAL` con unidad y `OPTION`), una **presentación base** (la tableta) y una presentación con **factor de conversión** (la caja x 100) con **dos códigos EAN**.

**Filas del Excel:** ID 45 — detalle y decisiones en [00-datos-del-excel.md](00-datos-del-excel.md).

Antes de empezar revise los [requisitos comunes](../README.md#antes-de-empezar).

**Usuarios:** ejecútelo con `admin.test`. Qué puede hacer cada usuario de prueba, qué permiso exige cada URL y ejemplos de uso con cada uno: [USUARIOS.md](USUARIOS.md).

## Orden de ejecución

Ejecute los archivos **en este orden**. Cada paso usa `id` guardados en pasos anteriores.

| Paso | Archivo | Qué hace | Llamadas | Depende de |
| --- | --- | --- | --- | --- |
| 00 | [00-datos-del-excel.md](00-datos-del-excel.md) | Leer: qué dice el Excel y cómo se interpreta | — | — |
| 01 | [01-consultar-datos-base.md](01-consultar-datos-base.md) | Obtener los `id` de lo que ya existe (unidad, empaque, tipos de grupo y fabricante) y registrar el fabricante si todavía no existe. | 9 | — |
| 02 | [02-crear-unidad-mg.md](02-crear-unidad-mg.md) | Tener una unidad para expresar la concentración (500 mg). | 1 | — |
| 03 | [03-crear-marca.md](03-crear-marca.md) | Registrar la marca comercial que el Excel esconde dentro del nombre. | 1 | — |
| 04 | [04-crear-categorias.md](04-crear-categorias.md) | Crear el árbol `MEDICAMENTOS > MEDICAMENTOS_ETICOS` donde se clasifica el producto. | 2 | — |
| 05 | [05-crear-atributos.md](05-crear-atributos.md) | Definir los datos técnicos que describen al medicamento: principio activo, concentración y forma farmacéutica. | 6 | 02 |
| 06 | [06-asociar-atributos-a-la-categoria.md](06-asociar-atributos-a-la-categoria.md) | Indicar qué atributos usan los productos de `MEDICAMENTOS_ETICOS` y cuáles son obligatorios. | 3 | 04, 05 |
| 07 | [07-crear-producto.md](07-crear-producto.md) | Registrar el producto global con sus datos mínimos, marca y fabricante. | 1 | 01, 03 |
| 08 | [08-clasificar-producto.md](08-clasificar-producto.md) | Asignar la categoría principal y ver qué atributos quedan exigidos. | 3 | 04, 07 |
| 09 | [09-registrar-valores-de-atributos.md](09-registrar-valores-de-atributos.md) | Dar valor a los tres atributos obligatorios. | 3 | 05, 07 |
| 10 | [10-crear-presentaciones.md](10-crear-presentaciones.md) | Registrar cómo se vende: por tableta suelta y por caja de 100. | 2 | 01, 07 |
| 11 | [11-registrar-codigos-de-barras.md](11-registrar-codigos-de-barras.md) | Asociar los dos EAN del Excel a la caja. | 2 | 07, 10 |
| 12 | [12-crear-y-asignar-grupos.md](12-crear-y-asignar-grupos.md) | Conservar la agrupación del sistema anterior (`Grupo 1` a `Grupo 4`). | 12 | 01, 07 |
| 13 | [13-verificar-resultado.md](13-verificar-resultado.md) | Comprobar que el producto quedó completo, elegible y que se encuentra por código y por atributos. | 3 | 07 |

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
| `<UND>` | 01 | 07 |
| `<BOX>` | 01 | 10 |
| `<GT_GROUP_1>` | 01 | 12 |
| `<GT_GROUP_2>` | 01 | 12 |
| `<GT_GROUP_3>` | 01 | 12 |
| `<GT_GROUP_4>` | 01 | 12 |
| `<PAIS_CO>` | 01 | — |
| `<FABRICANTE_SIEGFRIED>` | 01 | 07 |
| `<MG>` | 02 | 05 |
| `<MARCA_ADOREM>` | 03 | 07 |
| `<CAT_MEDICAMENTOS>` | 04 | — |
| `<CAT_MEDICAMENTOS_ETICOS>` | 04 | 06, 08 |
| `<ATR_PRINCIPIO_ACTIVO>` | 05 | 06, 09 |
| `<ATR_CONCENTRACION_MG>` | 05 | 06, 09 |
| `<ATR_FORMA_FARMACEUTICA>` | 05 | 06, 09 |
| `<OPC_TABLETA>` | 05 | 09 |
| `<OPC_CAPSULA>` | 05 | — |
| `<OPC_JARABE>` | 05 | — |
| `<CA_PRINCIPIO_ACTIVO>` | 06 | — |
| `<CA_CONCENTRACION_MG>` | 06 | — |
| `<CA_FORMA_FARMACEUTICA>` | 06 | — |
| `<PRODUCTO>` | 07 | 08, 09, 10, 11, 12, 13 |
| `<PC_ETICOS>` | 08 | — |
| `<PRES_TABLETA>` | 10 | — |
| `<PRES_CAJA_X100>` | 10 | 11 |
| `<ID_EAN_1>` | 11 | — |
| `<ID_EAN_2>` | 11 | — |
| `<GRUPO1_0001>` | 12 | — |
| `<ASIG_GRUPO1>` | 12 | — |
| `<GRUPO2_0012>` | 12 | — |
| `<ASIG_GRUPO2>` | 12 | — |
| `<GRUPO3_0085>` | 12 | — |
| `<ASIG_GRUPO3>` | 12 | — |
| `<GRUPO4_0170>` | 12 | — |
| `<ASIG_GRUPO4>` | 12 | — |

Las variables con `—` no se usan más en este ejercicio, pero conviene guardarlas: son las que se necesitan para corregir o inactivar ese registro después.

## Resultado esperado

Al terminar el paso 13 ([13-verificar-resultado.md](13-verificar-resultado.md)) el producto queda como se describe allí.

[Empezar → paso 01](01-consultar-datos-base.md)
