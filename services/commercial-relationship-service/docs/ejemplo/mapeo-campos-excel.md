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
| `Costo` | `reference_cost` | Costo de referencia (4 decimales); no reemplaza el costo histórico de Inventory. Vacío en las filas usadas → `0` |

El producto global (nombre canónico, marca, unidad, códigos de barras, categorías, atributos) vive en Product
Catalog: Commercial Relationship guarda solo su `id` (`global_product_id`).

## Columnas que no pertenecen a esta fase

| Columna del Excel | Dónde va | Motivo |
| --- | --- | --- |
| `Precio Lista 1` … `Precio Lista 18` | Commercial Relationship, **Fase B** (`price_lists`, `price_list_items`) | Las listas de precios llegan en la Fase B. En la Fase A solo existe el precio simple `sale_price` (con su moneda), vacío en las filas usadas |
| `Nombre Proveedor`, referencia del proveedor dentro del nombre (`RF…`) | Commercial Relationship, **Fase B** (`supplier_products`) | Es cómo llama el proveedor al producto |
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
