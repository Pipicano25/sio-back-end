# Datos del ejercicio — Ejercicio 1 — Adopción de productos del Excel

[← Orden del ejercicio](ORDEN.md)

> **Datos reales del sistema anterior.** Los productos son filas de `docs/CAMPOS PRODUCTOS.xlsx` (se cita la fila de cada uno). Mapeo de columnas: [../mapeo-campos-excel.md](../mapeo-campos-excel.md). La empresa y los datos marcados como **ficticios** son inventados.

## Datos usados

| Dato | Valor |
| --- | --- |
| Fuente | `docs/CAMPOS PRODUCTOS.xlsx`, hoja `Hoja1` (encabezados en la fila 2) |
| Fila 40 | `Código` 000045 · `Referencia` 48691 · `Nombre` ACETAMINOFEN (ADOREM) 500MG TABLETA CAJAX100 SIEGFRIED · `Nombre Corto` ACETAMINOFEN · `Control Inventario` S · `Maneja Lotes` S · `Maneja Fecha Vencimiento` S · `Código Barras 1` 7707355056876 |
| Fila 413 | `Código` 000537 · `Referencia` 71430 · `Nombre` AGUJA 18GX1 1/2 CAJAX100 RFZC18B RYMCO · `Nombre Corto` AGUJA 18GX1 1/2 · `Control Inventario` S · `Maneja Lotes` S · `Maneja Fecha Vencimiento` S · `Código Barras 2` 7706634002856 |
| Fila 11499 | `Código` 015721 · `Referencia` 74865 · `Nombre` WINNY GOLD ETAPA 6 XXXG PAQUETEX30 TECNOQUIMICAS · `Código Barras 1` 7701021118264 |
| Fila 16610 | `Código` 022348 · `Referencia` NT · `Nombre` CEPILLO COLGATE INFANTIL 2-5 AÑOS EXTRA SUAVE NIÑA PACK X2 · `Estado` I · `Maneja Lotes` S · `Maneja Fecha Vencimiento` N |
| Precios y costos | Las cuatro filas tienen `Precio Lista 1` y `Costo` **vacíos**: se adoptan con el precio y el costo por defecto (`0`). El precio en pesos chilenos del paso 05 es **ficticio** y solo ilustra los decimales por moneda. |
| Producto incompleto | **Ficticio**: un producto global sin completar en Product Catalog, para mostrar el rechazo por elegibilidad. |
| Empresa | DROGUERÍA EJEMPLO FICTICIA S.A.S. (**ficticia**), registrada en Operational Context. |

## Cómo se interpretan

| Tema | Decisión |
| --- | --- |
| Qué se adopta | Cada fila del Excel es un producto del catálogo **de la empresa**; el producto global ya existe en Product Catalog (ejercicios de ese servicio). Se adopta con su `id`, no con sus datos. |
| Código y referencia | `Código` → `internal_code` (único en la empresa, sin distinguir mayúsculas); `Referencia` → `reference_code` (no único). |
| Nombre visible | `Nombre` → `display_name` y `Nombre Corto` → `short_name`: los escribe el usuario; el servicio no los copia de Product Catalog ni los sugiere (DS-14). |
| Inventario | `Control Inventario`, `Maneja Lotes` y `Maneja Fecha Vencimiento` (`S`/`N`) → las tres banderas. Lotes exige control de inventario y vencimiento exige lotes. |
| Producto inactivo | La fila 16610 tiene `Estado = I`: en Product Catalog quedó `INACTIVE` y no se puede adoptar. |
| Primer uso | Antes de guardar, el servicio registra el **primer uso** del producto en Product Catalog con su propia identidad técnica; si falla, no se guarda nada (DS-01). |
| Moneda | Lista cerrada de 38 monedas con sus decimales ISO 4217: `COP` admite 2 decimales, `CLP` ninguno. |

[Empezar → paso 01](01-consultar-datos-base.md)
