# Ejercicio 4 — Presentaciones de un producto empresarial

[← Todos los ejercicios](../README.md)

**Qué enseña:** **Adoptar presentaciones** globales para un producto ya adoptado, marcar la **predeterminada de compra** y ver cómo marcar otra **retira la marca anterior en la misma operación**, el **rechazo** de una presentación de otro producto y de una adopción repetida, e **inactivar** la predeterminada (pierde la marca).

**Datos:** **reales** del sistema anterior (`docs/CAMPOS PRODUCTOS.xlsx`) — detalle y decisiones en [00-datos-del-excel.md](00-datos-del-excel.md).

Antes de empezar revise los [requisitos comunes](../README.md#antes-de-empezar).

**Usuarios:** ejecútelo con `admin.test`. Qué puede hacer cada usuario de prueba, qué permiso exige cada URL y ejemplos de uso con cada uno: [USUARIOS.md](USUARIOS.md).

## Orden de ejecución

Ejecute los archivos **en este orden**. Cada paso usa `id` guardados en pasos anteriores.

| Paso | Archivo | Qué hace | Llamadas | Depende de |
| --- | --- | --- | --- | --- |
| 00 | [00-datos-del-excel.md](00-datos-del-excel.md) | Leer: las filas del Excel y cómo se interpretan | — | — |
| 01 | [01-consultar-datos.md](01-consultar-datos.md) | Obtener `<EMPRESA>`, el producto global y las presentaciones. | 6 | — |
| 02 | [02-adoptar-producto.md](02-adoptar-producto.md) | Crear el producto empresarial al que pertenecerán las presentaciones. | 1 | 01 |
| 03 | [03-adoptar-presentaciones.md](03-adoptar-presentaciones.md) | Adoptar la caja como predeterminada de compra y luego el sobre, que toma la marca. | 3 | 01, 02 |
| 04 | [04-rechazos.md](04-rechazos.md) | Presentación de otro producto y adopción repetida. | 2 | 01, 02 |
| 05 | [05-inactivar-y-consultar.md](05-inactivar-y-consultar.md) | Inactivar el sobre (pierde la marca) y listar las presentaciones del producto. | 2 | 01, 02, 03 |

## Por qué este orden

1. **Producto adoptado primero.** La presentación empresarial pertenece a un producto empresarial `ACTIVE`.
2. **Marcar antes de inactivar.** Se inactiva la predeterminada para mostrar que pierde la marca.

## Lista de `id` que debe ir guardando

| Variable | Se obtiene en | Se usa en |
| --- | --- | --- |
| `<EMPRESA>` | 01 | 02, 03, 04, 05 |
| `<GP_ACETAMINOFEN>` | 01 | 02 |
| `<GPRES_CAJA>` | 01 | 03, 04 |
| `<GPRES_SOBRE>` | 01 | 03 |
| `<GP_AGUJA>` | 01 | — |
| `<GPRES_AGUJA>` | 01 | 04 |
| `<PRODUCTO>` | 02 | 03, 04, 05 |
| `<PRES_CAJA>` | 03 | — |
| `<PRES_SOBRE>` | 03 | 05 |

[Empezar → paso 01](01-consultar-datos.md)
