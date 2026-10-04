# Ejercicio 1 — Adopción de productos del Excel

[← Todos los ejercicios](../README.md)

**Qué enseña:** **Adoptar** productos globales en la empresa con los datos privados del sistema anterior (código interno, referencia, nombre corto, lotes, vencimiento, control de inventario), ver los **rechazos** de un producto inactivo, uno incompleto, una adopción repetida y un código repetido, cambiar **precio y moneda** respetando los decimales de cada moneda, consultar por lotes e **inactivar y reactivar**.

**Datos:** **reales** del sistema anterior (`docs/CAMPOS PRODUCTOS.xlsx`) — detalle y decisiones en [00-datos-del-excel.md](00-datos-del-excel.md).

Antes de empezar revise los [requisitos comunes](../README.md#antes-de-empezar).

**Usuarios:** ejecútelo con `admin.test`. Qué puede hacer cada usuario de prueba, qué permiso exige cada URL y ejemplos de uso con cada uno: [USUARIOS.md](USUARIOS.md).

## Orden de ejecución

Ejecute los archivos **en este orden**. Cada paso usa `id` guardados en pasos anteriores.

| Paso | Archivo | Qué hace | Llamadas | Depende de |
| --- | --- | --- | --- | --- |
| 00 | [00-datos-del-excel.md](00-datos-del-excel.md) | Leer: las filas del Excel y cómo se interpretan | — | — |
| 01 | [01-consultar-datos-base.md](01-consultar-datos-base.md) | Obtener `<EMPRESA>` y los `id` de los productos globales. | 6 | — |
| 02 | [02-adoptar-acetaminofen.md](02-adoptar-acetaminofen.md) | Adoptar el producto con lotes y vencimiento. | 1 | 01 |
| 03 | [03-adoptar-aguja.md](03-adoptar-aguja.md) | Adoptar un segundo producto de la misma empresa. | 1 | 01 |
| 04 | [04-rechazos.md](04-rechazos.md) | Ver los errores de elegibilidad y de unicidad. | 5 | 01 |
| 05 | [05-precio-y-moneda.md](05-precio-y-moneda.md) | Mostrar los decimales de cada moneda (precio **ficticio**). | 2 | 03 |
| 06 | [06-consultar-y-estados.md](06-consultar-y-estados.md) | Ver el listado, la consulta por lotes y el ciclo de vida. | 4 | 01, 02, 04 |
| 07 | [07-resumen-de-empresas.md](07-resumen-de-empresas.md) | Recorrer, una por página, las empresas del usuario con sus conteos (FR-046). | 1 | — |

## Por qué este orden

1. **Empresa y productos globales primero.** La adopción une una empresa (Operational Context) con un producto global (Product Catalog); ambos deben existir antes.
2. **Adoptar antes de cambiar.** Los cambios de precio, moneda y estado se hacen sobre el producto empresarial.
3. **Rechazos después de una adopción.** La adopción repetida y el código repetido necesitan una adopción previa.

## Lista de `id` que debe ir guardando

| Variable | Se obtiene en | Se usa en |
| --- | --- | --- |
| `<EMPRESA>` | 01 | 02, 03, 04, 06 |
| `<GP_ACETAMINOFEN>` | 01 | 02, 04 |
| `<GP_AGUJA>` | 01 | 03 |
| `<GP_WINNY>` | 01 | 04 |
| `<GP_CEPILLO>` | 01 | 04 |
| `<GP_INCOMPLETO>` | 01 | 04 |
| `<CP_ACETAMINOFEN>` | 02 | 06 |
| `<CP_AGUJA>` | 03 | 05 |
| `<CP_WINNY>` | 04 | 06 |

[Empezar → paso 01](01-consultar-datos-base.md)
