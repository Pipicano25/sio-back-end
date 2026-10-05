# Ejercicio 5 — Proveedores por producto y condiciones de pago

[← Todos los ejercicios](../README.md)

**Qué enseña:** Registrar qué **proveedor suministra** un producto en general y en una **presentación** concreta (relaciones que coexisten), los rechazos de una **relación repetida** y de una **unidad distinta de la base**, y las **condiciones de pago**: contado con plazo (rechazado) y crédito predeterminado en pesos.

**Datos:** **reales** del sistema anterior (`docs/CAMPOS PRODUCTOS.xlsx`) — detalle y decisiones en [00-datos-del-excel.md](00-datos-del-excel.md).

Antes de empezar revise los [requisitos comunes](../README.md#antes-de-empezar).

**Usuarios:** ejecútelo con `admin.test`. Qué puede hacer cada usuario de prueba, qué permiso exige cada URL y ejemplos de uso con cada uno: [USUARIOS.md](USUARIOS.md).

## Orden de ejecución

Ejecute los archivos **en este orden**. Cada paso usa `id` guardados en pasos anteriores.

| Paso | Archivo | Qué hace | Llamadas | Depende de |
| --- | --- | --- | --- | --- |
| 00 | [00-datos-del-excel.md](00-datos-del-excel.md) | Leer: las filas del Excel y cómo se interpretan | — | — |
| 01 | [01-consultar-datos.md](01-consultar-datos.md) | Obtener los identificadores de los otros servicios. | 7 | — |
| 02 | [02-preparar.md](02-preparar.md) | Crear lo que el producto de proveedor referencia. | 3 | 01 |
| 03 | [03-productos-de-proveedor.md](03-productos-de-proveedor.md) | Relación general, rechazo por unidad, relación por presentación y rechazo por repetición. | 4 | 01, 02 |
| 04 | [04-condiciones-de-pago.md](04-condiciones-de-pago.md) | Contado con plazo (rechazado) y crédito predeterminado. | 3 | 01, 02 |

## Por qué este orden

1. **Producto, presentación y proveedor primero.** El producto de proveedor une los tres.
2. **Unidad base antes de registrar.** El servicio la verifica en Product Catalog al registrar.

## Lista de `id` que debe ir guardando

| Variable | Se obtiene en | Se usa en |
| --- | --- | --- |
| `<EMPRESA>` | 01 | 02, 03, 04 |
| `<GP_ACETAMINOFEN>` | 01 | 02 |
| `<GPRES_CAJA>` | 01 | 02 |
| `<UNIDAD_BASE>` | 01 | 03 |
| `<ORG_PROVEEDOR>` | 01 | 02 |
| `<TIPO_CASH>` | 01 | 04 |
| `<TIPO_CREDIT>` | 01 | 04 |
| `<PRODUCTO>` | 02 | 03 |
| `<PRES_CAJA>` | 02 | 03 |
| `<PROVEEDOR>` | 02 | 03, 04 |
| `<PRV_GENERAL>` | 03 | — |

[Empezar → paso 01](01-consultar-datos.md)
