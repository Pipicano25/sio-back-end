# Ejercicio 6 — Listas de precios y precio aplicable

[← Todos los ejercicios](../README.md)

**Qué enseña:** Crear una **lista de precios predeterminada**, registrar el **precio** real de la fuente, ver el rechazo de un **precio solapado** y de un **precio en vigencia modificado**, **cambiar el precio** con vigencia futura y resolver el **precio aplicable** con precio de lista, con **respaldo** en el precio simple y **sin respaldo** cuando se indica una lista explícita.

**Datos:** **reales** del sistema anterior (`docs/CAMPOS PRODUCTOS.xlsx`) — detalle y decisiones en [00-datos-del-excel.md](00-datos-del-excel.md).

Antes de empezar revise los [requisitos comunes](../README.md#antes-de-empezar).

**Usuarios:** ejecútelo con `admin.test`. Qué puede hacer cada usuario de prueba, qué permiso exige cada URL y ejemplos de uso con cada uno: [USUARIOS.md](USUARIOS.md).

## Orden de ejecución

Ejecute los archivos **en este orden**. Cada paso usa `id` guardados en pasos anteriores.

| Paso | Archivo | Qué hace | Llamadas | Depende de |
| --- | --- | --- | --- | --- |
| 00 | [00-datos-del-excel.md](00-datos-del-excel.md) | Leer: las filas del Excel y cómo se interpretan | — | — |
| 01 | [01-consultar-datos.md](01-consultar-datos.md) | Obtener `<EMPRESA>` y los productos globales. | 3 | — |
| 02 | [02-adoptar-productos.md](02-adoptar-productos.md) | Crear los productos empresariales. | 2 | 01 |
| 03 | [03-lista-y-precio.md](03-lista-y-precio.md) | Lista predeterminada en COP con el precio real y el rechazo por solapamiento. | 3 | 01, 02 |
| 04 | [04-cambiar-precio.md](04-cambiar-precio.md) | Un precio en vigencia no se reescribe; se usa change-price. | 2 | 03 |
| 05 | [05-precio-aplicable.md](05-precio-aplicable.md) | Precio de lista, respaldo en el precio simple y lista explícita sin precio. | 3 | 01, 02, 03 |

## Por qué este orden

1. **Productos y lista antes de precios.** El precio une una lista y un producto empresarial `ACTIVE`.
2. **Cambiar antes de resolver en el futuro.** La consulta con `at` en 2099 muestra el precio nuevo.

## Lista de `id` que debe ir guardando

| Variable | Se obtiene en | Se usa en |
| --- | --- | --- |
| `<EMPRESA>` | 01 | 02, 03, 05 |
| `<GP_IRBESARTAN>` | 01 | 02 |
| `<GP_ACETAMINOFEN>` | 01 | 02 |
| `<IRBESARTAN>` | 02 | 03, 05 |
| `<ACETAMINOFEN>` | 02 | 05 |
| `<LISTA>` | 03 | 05 |
| `<PRECIO>` | 03 | 04 |
| `<PRECIO_NUEVO>` | 04 | — |

[Empezar → paso 01](01-consultar-datos.md)
