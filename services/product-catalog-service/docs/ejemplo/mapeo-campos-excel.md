# Mapeo de las columnas del Excel al catálogo

[← Todos los ejercicios](README.md)

`docs/CAMPOS PRODUCTOS.xlsx` es una exportación de un sistema anterior. Su primera fila agrupa las
columnas por servicio (`Product Catalog Service`, `Commercial Relationship Service`). Este documento
indica **dónde queda cada columna** según la spec del catálogo.

> **Diferencia importante con el Excel.** El Excel marca como "Product Catalog Service" varias
> columnas que la spec deja **fuera** del catálogo porque dependen de cada empresa (stock,
> ubicación, bodega, promociones, impuestos, inventario actual…). El catálogo solo guarda lo que
> define al producto para todas las empresas (FR-001). Esas columnas aparecen abajo como
> "Fuera del catálogo", con el servicio que corresponde.

## Columnas que sí van al catálogo

| Columna del Excel | Destino en el catálogo | Cómo se traduce | Ejercicio |
| --- | --- | --- | --- |
| `Nombre` | `canonical_name` del producto | Se separa lo que es del producto de lo que es de la presentación, la marca y el fabricante. `ACETAMINOFEN (ADOREM) 500MG TABLETA CAJAX100 SIEGFRIED` → producto "Acetaminofén 500 mg tableta", marca Adorem, presentación "Caja x 100", fabricante Siegfried. | 1 |
| `Nombre Tipo Producto` (`ETICOS`, `LECHES`, `PAÑALES`, `HOSPITALARIOS`, `CONSUMO`…) | Categoría | Es la clasificación principal; se ubica en un árbol (p. ej. `MEDICAMENTOS > MEDICAMENTOS_ETICOS`). Cuando el valor es demasiado amplio (`CONSUMO`), la categoría se define por lo que es el producto. | 1–5 |
| `Unidad Medida` (`CAJA`, `LATA`, `PAQUETE`, `PACK`…) | **Tipo de empaque** de la presentación | Pese al nombre de la columna, `CAJA` o `LATA` no son unidades de medida sino empaques (`BOX`, `CAN`…). La unidad base del producto suele ser `UND` (o `G` si se vende por peso). | 1–5 |
| `Contenido Interno` (100, 30…) | `base_quantity` de la presentación | "Caja x 100" → presentación `BOX` con `base_quantity = 100`. Si viene vacío, se toma del nombre (`PACK X2`). | 1, 3, 4, 5 |
| `Decimales en Cantidad` | `allows_decimals` de la unidad base | Si el producto se vende fraccionado, su unidad base debe admitir decimales. En este Excel es 0 en todas las filas. | — |
| `Código Barras 1`, `2`, `3` | Identificadores | Normalmente `EAN` (13 dígitos) o `GTIN` (14). Se registra **una vez** cada código distinto, ligado a su presentación. Los que no cumplen GS1 se revisan uno a uno. | 1–5 |
| `Estado` (`A`, `I`) | `status` (`ACTIVE`, `INACTIVE`) | Todo producto se crea activo; uno `I` se inactiva al final. | 5 |
| `Color`, `Talla`, `Base de Tela` | Atributos `OPTION` | En este Excel vienen **vacíos**; la talla, cuando existe, está en el nombre. | 3 |
| `Peso (Kg)`, `Metros (Cúbicos)` | Atributos `DECIMAL` con unidad | Solo si la categoría los necesita (en este Excel vienen en 0). | — |
| `Nombre Inglés`, `Observación` | Atributo `TEXT` / `description` | Opcionales (vacíos en este Excel). | — |
| `Grupo 1` … `Grupo 15` (código y nombre) | Tipos `GROUP_1` … `GROUP_15` y sus grupos | Se crea un grupo por par código/nombre (se consulta antes, porque lo comparten muchos productos) y se asigna al producto. `NO APLICA` no se importa. | 1–5 |
| `Colección` | Tipo de grupo `COLECCION` | Con `allows_multiple: true` si un producto puede estar en varias. Vacía en este Excel. | — |

## Columnas que parecen del catálogo pero no lo son

| Columna del Excel | Por qué no va al catálogo | Dónde va |
| --- | --- | --- |
| `Marca` / `Nombre Marca` | Vale `GENERAL` en 16 883 de 16 889 filas: no identifica una marca | La marca real se saca del nombre (ejercicios 1, 2, 3 y 5). |
| `Grupo 4` (`SIEGFRIED`, `NESTLE`, `RYMCO`…) | Es el laboratorio o la línea comercial | Fabricante → `manufacturer_organization_id` (Party Identity). Se conserva además como grupo. |
| `Grupo 6` = `EXCLUIR VIERNES DAO` | Es una regla comercial de una empresa, no una característica del producto | Commercial Relationship (ejercicios 2 y 3). |
| `Código` (`000045`, `022348`…) | Es el código interno de la empresa | `CompanyProduct.internal_code` (Commercial Relationship). |
| `Referencia` | Referencia propia de la empresa | `CompanyProduct.reference_code`. |
| Referencia del fabricante dentro del nombre (`RFZC18B`) | Sí identifica al producto | Identificador `OTHER` del catálogo (ejercicio 4). |
| Referencia del proveedor dentro del nombre (`RF12495528`) | Es del proveedor | `SupplierProduct` (Commercial Relationship) (ejercicio 2). |
| `Nombre Corto` | Nombre que usa la empresa | `CompanyProduct.short_name`. |
| `Nombre Proveedor` | Cómo lo llama el proveedor | `SupplierProduct` (Commercial Relationship). |
| `Precio Lista 1` … `18`, `Costo`, `Costo Promedio`, `Costo + Otros Impuestos`, `Costo Para Cotización Dotaciones` | Precios y costos de la empresa | Commercial Relationship / Inventory. |
| `Stock Mínimo`, `Stock Máximo`, `Ubicación`, `Bodega Almacenamiento`, `Inventario Actual`, `Lote` | Inventario de la empresa | Inventory Service. |
| `Maneja Lotes`, `Maneja Fecha Vencimiento`, `Control Inventario` | Cómo gestiona la empresa el producto | `CompanyProduct` (Commercial Relationship). |
| `% Impuesto`, `Tipo Impuesto`, `Tarifa Retención en la Fuente`, `Código DIAN`, `Unidad de Medida DIAN`, `Codigodian`, `Clasificación Arancelaria` | Clasificación tributaria y regulatoria | Sin dueño definido todavía (OP-04 y OP-05 de la spec). No se guarda en el catálogo. |
| `Venta Mínima`, `Múltiplo Venta`, `Permite Descuento`, `Promoción`, `Texto Promoción`, `Es Obsequio`, `Producto a Obsequiar`, `Liquida Puntos CRM`, `Aplica para E-Commerce`, `Ecommerce` | Condiciones comerciales de la empresa | Commercial Relationship / Sales. |
| `Tiempo de Garantia`, `Tiempo de Cambio`, `Permite Cambio` | Política comercial de la empresa | Commercial Relationship / Sales. |
| `Id/Nombre Centro de Costos`, `ID/Nombre Tercero Ingreso`, `ID/Nombre Tercero IVA`, `% Valor Recibido Para Terceros` | Datos contables | Finanzas (fuera del MVP). |
| `Tiempo Despacho Mesa`, `Controla Terminos de Asado o Fritura`, `Desayuno Hotel`, `Control por Peso`, `Código Inteligente - …` | Configuración de punto de venta | Sales. |
| `Tipo` (`Medicamento` en 16 879 filas) | No distingue productos | Se descarta; el tipo del catálogo es `GOOD`. |
| `Maneja Presentaciones` | En el catálogo todo producto tiene presentaciones | Se descarta (ejercicio 2). |

## Lo que el Excel revela sobre la calidad de los datos

Resultados de revisar las 16 889 filas con las reglas del catálogo:

| Hallazgo | Cantidad | Qué hace el catálogo |
| --- | --- | --- |
| Valores en las columnas de código de barras que no son GS1 válidos (longitud o dígito de control) | 2 228 | No se aceptan como `EAN`/`GTIN`/`UPC` (`422`); se revisan uno a uno. |
| Valores de código de barras **iguales a la columna `Código`** (el código interno copiado en el campo de código de barras) | 482 | No se registran en el catálogo (ejercicio 5). |
| Códigos distintos que aparecen más de una vez (en el mismo producto o en varios) | 109 | Se registran una sola vez; si chocan entre productos distintos, `409 IDENTIFIER_COLLISION`. |
| Códigos compartidos por **dos productos distintos** | 2 | Colisión que debe resolver una persona. |
| Productos que en el Excel son filas separadas pero en el catálogo son **un producto con varias presentaciones** (mismo nombre, distinto tamaño) | varios | Se cargan como un producto (ejercicio 2). El servicio avisa `POSSIBLE_DUPLICATE` si se crea dos veces el mismo nombre con la misma marca. |
| Productos con `Maneja Presentaciones = S` | 4 152 | Todos tendrán al menos una presentación en el catálogo. |
| Grupos que no corresponden al producto (un cepillo en `MEDICO QUIRURGICOS`) | — | Se importan como vienen; la clasificación correcta la da la categoría (ejercicio 5). |
