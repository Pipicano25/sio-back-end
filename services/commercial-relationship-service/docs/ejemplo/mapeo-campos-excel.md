# Mapeo de columnas del Excel a Commercial Relationship

[← Todos los ejercicios](README.md)

Fuente: `docs/CAMPOS PRODUCTOS.xlsx`, hoja `Hoja1` (fila 1: servicio sugerido; fila 2: encabezados). Este
documento completa el mapeo general de Product Catalog
(`services/product-catalog-service/docs/ejemplo/mapeo-campos-excel.md`), que asigna cada columna a un
servicio: aquí se detalla lo que corresponde a **Commercial Relationship Service**.

## Columnas que van a `CompanyProduct` (Fase A)

| Columna del Excel | Campo | Regla |
| --- | --- | --- |
| `Código` | `internal_code` | Código interno de la empresa; único en la empresa sin distinguir mayúsculas; se puede cambiar (DS-07) |
| `Referencia` | `reference_code` | Referencia propia de la empresa; no es única (`NT` = sin referencia) |
| `Nombre` | `display_name` | Nombre visible en la empresa; lo escribe el usuario, el servicio no lo copia del producto global (DS-14) |
| `Nombre Corto` | `short_name` | Nombre corto opcional |
| `Control Inventario` (`S`/`N`) | `inventory_control_enabled` | `S` → `true` |
| `Maneja Lotes` (`S`/`N`) | `lot_tracking_enabled` | Exige control de inventario |
| `Maneja Fecha Vencimiento` (`S`/`N`) | `expiration_tracking_enabled` | Exige lotes |
| `Costo` | — | No se carga en el producto empresarial (spec 019: sin `reference_cost`); los costos vienen de las compras y de Inventory |

El producto global (nombre canónico, marca, unidad, códigos de barras, categorías, atributos) vive en Product
Catalog: Commercial Relationship guarda solo su `id` (`global_product_id`).

## Columnas que van a la Fase B (feature 010)

| Columna del Excel | Entidad y campo | Regla |
| --- | --- | --- |
| `Precio Lista 1` … `Precio Lista 18` | Una `PriceList` por columna (p. ej. código `LISTA-10`) y un `PriceListItem` con `unit_price` por presentación (spec 019) | Moneda de la lista con sus decimales; `0` es un precio real, la ausencia de precio se representa sin registro. En toda la fuente solo la **fila 16577** tiene un precio por lista (`Precio Lista 10` = 30420; ejercicio 6); las demás tienen `0` o vacío |
| `Nombre Proveedor` | `SupplierProduct.supplier_product_code` | Cómo llama el proveedor al producto (máximo 100 caracteres). La fila 40 se usa en el ejercicio 5 |
| `Maneja Presentaciones`, `Contenido Interno` | Indican que el producto tiene presentaciones (`CompanyProductPresentation`) | La presentación global (nombre, cantidad base, empaque) vive en Product Catalog; la empresa solo adopta su `id` y le pone su código o SKU. La fuente no trae presentaciones por fila: las de los ejercicios son ficticias |

## Columnas que no pertenecen a este servicio

| Columna del Excel | Dónde va | Motivo |
| --- | --- | --- |
| `Costo Promedio`, `Costo + Otros Impuestos` | Inventory | Valoración de inventario |
| `Stock Mínimo`, `Stock Máximo`, `Ubicación`, `Lote` | Inventory | Existencias y políticas por sucursal |
| `% Impuesto`, `Tipo Impuesto` | Sin dueño definido aún | Tributario |
| `Estado` (`A`/`I`) | Product Catalog (estado del producto global) | La fila 16610 (`I`) es un producto global `INACTIVE`: no se puede adoptar |
| `Venta Mínima`, `Múltiplo Venta`, `Permite Descuento`, `Promoción`, garantías | Commercial Relationship / Sales (fases posteriores) | Condiciones comerciales |
| Centros de costo, terceros, `% Valor Recibido Para Terceros` | Finanzas (fuera del MVP) | Contables |

## Filas usadas en el ejercicio 1

| Fila | `Código` | `Referencia` | `Nombre Corto` | Inventario / Lotes / Vencimiento | Uso |
| --- | --- | --- | --- | --- | --- |
| 40 | 000045 | 48691 | ACETAMINOFEN | S / S / S | Adopción con lotes y vencimiento |
| 413 | 000537 | 71430 | AGUJA 18GX1 1/2 | S / S / S | Adopción; cambio de precio y moneda |
| 11499 | 015721 | 74865 | WINNY GOLD ETAPA 6 XXXG PAQUETEX30 TECNOQUIMICAS | S / S / S | Código interno repetido y adopción con su código |
| 16610 | 022348 | NT | CEPILLO COLGATE INFANTIL 2-5 AÑOS EXTRA SUAVE NIÑA PACK X2 | S / S / N | Producto global inactivo (`Estado = I`): rechazo |

## Filas usadas en los ejercicios 4–6 (Fase B)

| Fila | `Código` | Columnas usadas | Uso |
| --- | --- | --- | --- |
| 40 | 000045 | `Maneja Presentaciones` S, `Contenido Interno` 100, `Nombre Proveedor` ACETAMINOFEN 500MG TABLETA CAJAX100 SIEGFRIED | Presentaciones (ejercicio 4); producto de proveedor con su código (ejercicio 5); producto sin precio de lista (ejercicio 6) |
| 413 | 000537 | — | Presentación de otro producto: rechazo (ejercicio 4) |
| 16577 | 022315 | `Precio Lista 10` 30420, `Código Barras 1` 7702057716226 | Lista de precios y precio real (ejercicio 6) |
