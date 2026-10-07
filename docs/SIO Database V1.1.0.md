# 1. Diseño de bases de datos — SIO Database

**Versión:** `1.1.0`  
**Motivo de actualización:**

- incorporación de catálogos maestros de geografía, sector económico y pagos
- generalización de identidad de personas; representante legal y asesor SIO
- condiciones de pago de clientes y proveedores
- georreferenciación de empresas y sucursales
- creación del dominio financiero para cuentas por cobrar, cuentas por pagar y pagos.

---

## 2. Propósito

Presenta las entidades organizadas por microservicio y base de datos con su finalidad, alcance, atributos, tipos PostgreSQL, reglas, restricciones y relaciones principales.

El diseño aplica las siguientes decisiones:

- Cada microservicio es propietario de su propia base de datos.
- No existen llaves foráneas entre bases de datos de microservicios distintos.
- Las referencias entre servicios se almacenan como identificadores `UUID`.
- Las entidades globales reducen duplicados y pueden reutilizarse entre empresas.
- Los datos básicos de contacto de personas y organizaciones se administran globalmente mediante perfiles versionados con una única versión activa.
- Las direcciones se almacenan de forma estructurada mediante dirección, ciudad, departamento/estado, país y código postal cuando aplique.
- Países, divisiones administrativas, ciudades, sectores económicos, tipos de condición de pago y medios de pago se gobiernan mediante catálogos maestros y no se registran como texto libre en las entidades operativas cuando existe un catálogo aplicable.
- La identidad global de una persona se representa mediante `PersonIdentity` independientemente de que actúe como cliente, representante legal u otro rol.
- Las reglas de formato para números de identificación se gobiernan mediante `IdentificationTypeRule` por tipo de parte, país y tipo de identificación.
- Keycloak conserva credenciales, sesiones, tokens y roles.
- Los nombres internos se manejan en inglés y `snake_case`.
- Las fechas y horas se almacenan con `TIMESTAMPTZ`.
- La zona horaria operativa predeterminada es `America/Bogota`.
- `Parameter` continúa aplazado hasta que exista una necesidad funcional concreta que justifique un catálogo genérico de parámetros.

---

## 3. Convenciones generales

| Concepto                   | Tipo PostgreSQL | Uso                                                     |
| -------------------------- | --------------- | ------------------------------------------------------- |
| Identificadores            | `UUID`          | Llaves primarias y referencias entre servicios.         |
| Texto corto                | `VARCHAR(n)`    | Códigos, nombres y estados.                             |
| Texto largo                | `TEXT`          | Descripciones, observaciones y motivos.                 |
| Valores monetarios         | `NUMERIC(18,2)` | Totales, impuestos, descuentos y límites.               |
| Costos o precios unitarios | `NUMERIC(18,4)` | Valores unitarios con mayor precisión.                  |
| Cantidades                 | `NUMERIC(18,4)` | Inventario, compras, ventas y ajustes.                  |
| Factores de conversión     | `NUMERIC(18,8)` | Conversión entre unidades.                              |
| Consecutivos               | `BIGINT`        | Valores numéricos secuenciales.                         |
| Números pequeños           | `SMALLINT`      | Número de línea o longitud.                             |
| Booleanos                  | `BOOLEAN`       | Estados binarios.                                       |
| Fechas de negocio          | `DATE`          | Fechas sin hora.                                        |
| Fecha y hora               | `TIMESTAMPTZ`   | Auditoría y eventos.                                    |
| Datos flexibles            | `JSONB`         | Parámetros, errores y payloads.                         |
| Moneda                     | `CHAR(3)`       | Código ISO 4217 por ejemplo `COP`.                      |
| Porcentajes                | `NUMERIC(7,4)`  | Márgenes, niveles de servicio, tasas y participaciones. |
| Duraciones                 | `NUMERIC(12,2)` | Horas observadas o esperadas para lead time y procesos. |
| Coordenadas geográficas    | `NUMERIC(9,6)`  | Latitud y longitud en grados decimales.                 |

| Código    | Significado                                                |
| --------- | ---------------------------------------------------------- |
| `PK`      | Llave primaria.                                            |
| `FK`      | Llave foránea dentro de la misma base de datos.            |
| `REF`     | Referencia a otro microservicio, sin llave foránea física. |
| `NN`      | Campo obligatorio, `NOT NULL`.                             |
| `UQ`      | Restricción única.                                         |
| `CK`      | Restricción `CHECK`.                                       |
| `DEFAULT` | Valor predeterminado.                                      |

---

# 4. Entidades globales compartidas por microservicio

---

## 4.1 GlobalCategory

**Tabla:** `global_categories`  
**Naturaleza:** global y compartida.  
**Servicio propietario:** Product Catalog Service.

### Descripción

Representa una clasificación estándar para organizar productos en toda SIO y evita que cada empresa cree variantes diferentes para un mismo concepto, como `Bebida`, `Bebidas` o `Refrescos`.

Puede organizarse jerárquicamente para construir una taxonomía común, por ejemplo `Alimentos` puede contener `Granos` y `Granos` puede contener `Arroz`.

La categoría solo define una clasificación conceptual y no debe contener precios, costos, inventario ni información comercial.

Una categoría usada históricamente no se elimina físicamente, se desactiva cuando ya no debe utilizarse en productos nuevos.

### Atributos

| Atributo             | Tipo           | Regla           | Descripción                                          |
| -------------------- | -------------- | --------------- | ---------------------------------------------------- |
| `id`                 | `UUID`         | PK, NN          | Identificador global de la categoría.                |
| `parent_category_id` | `UUID`         | FK, nullable    | Categoría superior; es nulo en el primer nivel.      |
| `code`               | `VARCHAR(50)`  | NN, UQ          | Código estable y normalizado.                        |
| `name`               | `VARCHAR(120)` | NN              | Nombre oficial.                                      |
| `description`        | `TEXT`         | nullable        | Explica qué productos incluye y cuáles quedan fuera. |
| `status`             | `VARCHAR(20)`  | NN, CK          | Estado `ACTIVE` o `INACTIVE`.                        |
| `version`            | `INTEGER`      | NN, DEFAULT `1` | Control de concurrencia.                             |
| `created_at`         | `TIMESTAMPTZ`  | NN              | Fecha de creación.                                   |
| `updated_at`         | `TIMESTAMPTZ`  | NN              | Última modificación.                                 |

### Reglas y restricciones

- `code` es único globalmente sin diferenciar mayúsculas y minúsculas.
- `parent_category_id` no puede apuntar al mismo registro.
- Se deben impedir ciclos jerárquicos.
- Una categoría inactiva no puede asignarse a productos nuevos.

### Relaciones

- Una categoría puede tener muchas categorías hijas mediante `parent_category_id`.
- Una categoría puede relacionarse con múltiples productos globales mediante `GlobalProductCategory`.
- Un mismo `GlobalProduct` puede pertenecer a múltiples categorías globales.

---

## 4.2 GlobalUnitOfMeasure

**Tabla:** `global_units_of_measure`  
**Naturaleza:** global y compartida.  
**Servicio propietario:** Product Catalog Service.

### Descripción

Representa una unidad estándar para medir cantidades y centraliza códigos como `UND`, `KG`, `G`, `LT` o `ML` evitando duplicados semánticos como `KILO`, `KILOGRAMO` y `KGS`.

Indica si una unidad admite cantidades decimales, por ejemplo una unidad física puede manejar valores enteros, mientras que un kilogramo puede admitir `1.25`.

### Atributos

| Atributo           | Tipo          | Regla           | Descripción                                  |
| ------------------ | ------------- | --------------- | -------------------------------------------- |
| `id`               | `UUID`        | PK, NN          | Identificador global.                        |
| `code`             | `VARCHAR(20)` | NN, UQ          | Código estándar, por ejemplo `KG`.           |
| `name`             | `VARCHAR(80)` | NN              | Nombre completo.                             |
| `symbol`           | `VARCHAR(16)` | NN              | Símbolo visible.                             |
| `measurement_type` | `VARCHAR(30)` | NN, CK          | `UNIT`, `MASS`, `VOLUME`, `LENGTH` o `AREA`. |
| `allows_decimals`  | `BOOLEAN`     | NN              | Permite cantidades fraccionadas.             |
| `status`           | `VARCHAR(20)` | NN, CK          | Estado `ACTIVE` o `INACTIVE`.                |
| `version`          | `INTEGER`     | NN, DEFAULT `1` | Control de versión.                          |
| `created_at`       | `TIMESTAMPTZ` | NN              | Creación.                                    |
| `updated_at`       | `TIMESTAMPTZ` | NN              | Última modificación.                         |

### Reglas y restricciones

- `code` es único globalmente.
- Una unidad utilizada históricamente no se elimina.
- Una unidad inactiva no puede asignarse a productos nuevos.

---

## 4.3 GlobalProduct

**Tabla:** `global_products`  
**Naturaleza:** global y compartida.  
**Servicio propietario:** Product Catalog Service.

### Descripción

Representa la identidad común de un producto y define qué es el producto independientemente de cómo lo compre, venda, identifique o almacene cada empresa.

Por ejemplo, un producto puede existir una sola vez dentro del catálogo global y ser adoptado posteriormente por múltiples empresas mediante CompanyProduct.

GlobalProduct contiene únicamente información propia e intrínseca del producto que puede reutilizarse entre empresas.

Las categorías se relacionan mediante GlobalProductCategory, la marca mediante GlobalBrand, los identificadores externos mediante GlobalProductIdentifier, las presentaciones mediante GlobalProductPresentation y las características adicionales mediante GlobalProductAttributeValue.

No almacena códigos internos empresariales, SKU privados, precios empresariales, costos privados, proveedores seleccionados, saldos de inventario ni políticas propias de una empresa.

### Atributos

| Atributo                       | Tipo           | Regla           | Descripción                                                      |
| ------------------------------ | -------------- | --------------- | ---------------------------------------------------------------- |
| `id`                           | `UUID`         | PK, NN          | Identificador global.                                            |
| `product_type`                 | `VARCHAR(20)`  | NN, CK          | Tipo general; inicialmente `GOOD`.                               |
| `canonical_name`               | `VARCHAR(200)` | NN              | Nombre global normalizado.                                       |
| `description`                  | `TEXT`         | nullable        | Descripción general.                                             |
| `global_brand_id`              | `UUID`         | FK, nullable    | Marca global asociada al producto.                               |
| `manufacturer_organization_id` | `UUID`         | REF, nullable   | Organización fabricante administrada por Party Identity Service. |
| `base_unit_id`                 | `UUID`         | FK, NN          | Unidad de control.                                               |
| `status`                       | `VARCHAR(20)`  | NN, CK          | Estado `ACTIVE` o `INACTIVE`.                                    |
| `version`                      | `INTEGER`      | NN, DEFAULT `1` | Control de versión.                                              |
| `created_at`                   | `TIMESTAMPTZ`  | NN              | Creación.                                                        |
| `updated_at`                   | `TIMESTAMPTZ`  | NN              | Modificación.                                                    |

### Consideración de escalabilidad y particionamiento

`GlobalProduct` debe mantenerse como una única entidad lógica y no debe crearse una tabla independiente por cada categoría, grupo, tipo de producto o vertical de negocio.

Las categorías y demás clasificaciones son datos administrables que pueden cambiar con el tiempo y se relacionan con el producto mediante entidades específicas.

Si en el futuro el volumen de `global_products` justifica particionamiento físico en PostgreSQL, puede evaluarse inicialmente una estrategia `HASH` utilizando `id` como clave de partición.

Al ser un UUID estable e inmutable, `id` permite una distribución independiente de atributos funcionales que pueden cambiar con el tiempo.

El particionamiento solo debe implementarse cuando el volumen, rendimiento o mantenimiento real de la tabla lo justifiquen.

### Reglas y restricciones

- `canonical_name` es obligatorio.
- `product_type` debe pertenecer al conjunto de tipos admitidos por Product Catalog Service.
- `global_brand_id`, cuando exista, debe referenciar una `GlobalBrand` activa al crear o modificar el producto.
- `manufacturer_organization_id`, cuando exista, referencia una organización administrada por Party Identity Service y no utiliza una llave foránea física.
- `base_unit_id` debe referenciar una `GlobalUnitOfMeasure` activa.
- Un producto utilizado históricamente no debe eliminarse físicamente; debe cambiarse a estado `INACTIVE`.
- Un producto `INACTIVE` no puede utilizarse para nuevas adopciones empresariales.
- No almacena precio empresarial, costo empresarial, SKU privado, saldo de inventario ni políticas privadas de una empresa.

### Relaciones

- Puede pertenecer a múltiples `GlobalCategory` mediante `GlobalProductCategory`.
- Puede pertenecer a una `GlobalBrand`.
- Utiliza una `GlobalUnitOfMeasure` como unidad base.
- Puede referenciar una organización fabricante administrada por Party Identity Service.
- Puede tener múltiples `GlobalProductPresentation`.
- Puede tener múltiples `GlobalProductIdentifier`.
- Puede tener múltiples clasificaciones mediante `GlobalProductGroupAssignment`.
- Puede tener múltiples valores de atributos mediante `GlobalProductAttributeValue`.
- Puede ser adoptado por múltiples empresas mediante `CompanyProduct`.

---

## 4.3.1 ProductAttributeDefinition

**Tabla:** `product_attribute_definitions`
**Naturaleza:** global y compartida.
**Servicio propietario:** Product Catalog Service.

### Descripción

Representa la definición global de una característica que puede utilizarse para describir productos de diferentes categorías dentro de SIO.

Permite establecer atributos reutilizables como `Color`, `Material`, `Capacidad RAM`, `Tamaño de pantalla`, `Cilindraje`, `Porcentaje de grasa` o cualquier otra característica específica requerida por un tipo de producto.

La entidad define **qué significa el atributo y qué tipo de dato admite**, pero no almacena el valor particular de ningún producto.

Los valores concretos pertenecen a `GlobalProductAttributeValue`.

Una misma definición puede reutilizarse en diferentes categorías cuando represente el mismo concepto, evitando crear atributos duplicados con nombres diferentes.

### Atributos

| Atributo             | Tipo           | Regla           | Descripción                                                  |
| -------------------- | -------------- | --------------- | ------------------------------------------------------------ |
| `id`                 | `UUID`         | PK, NN          | Identificador global de la definición.                       |
| `code`               | `VARCHAR(80)`  | NN, UQ          | Código estable y normalizado del atributo.                   |
| `name`               | `VARCHAR(120)` | NN              | Nombre visible del atributo.                                 |
| `description`        | `TEXT`         | NN              | Explica el significado y uso esperado del atributo.          |
| `data_type`          | `VARCHAR(20)`  | NN, CK          | Tipo de dato permitido para el valor.                        |
| `unit_of_measure_id` | `UUID`         | FK, nullable    | Unidad global asociada cuando el atributo requiere medición. |
| `status`             | `VARCHAR(20)`  | NN, CK          | Estado `ACTIVE` o `INACTIVE`.                                |
| `version`            | `INTEGER`      | NN, DEFAULT `1` | Control de concurrencia y cambios de definición.             |
| `created_at`         | `TIMESTAMPTZ`  | NN              | Fecha de creación.                                           |
| `updated_at`         | `TIMESTAMPTZ`  | NN              | Última modificación.                                         |

### Reglas y restricciones

- `code` es único globalmente y no debe cambiar una vez utilizado por productos.
- Los tipos inicialmente permitidos para `data_type` son `TEXT`, `INTEGER`, `DECIMAL`, `BOOLEAN`, `DATE` y `OPTION`.
- `unit_of_measure_id` solo debe utilizarse cuando el atributo represente una magnitud que requiera unidad.
- Una definición utilizada históricamente no se elimina físicamente; se cambia su estado a `INACTIVE`.
- Una definición `INACTIVE` no puede asignarse a nuevos productos.
- El atributo define únicamente la estructura y semántica del dato; no almacena valores particulares de productos.
- Atributos que representen el mismo concepto deben reutilizar una única definición global en lugar de crear duplicados por categoría.

### Relaciones

- Puede utilizar una unidad definida en `GlobalUnitOfMeasure`.
- Puede relacionarse con diferentes categorías mediante `GlobalCategoryAttribute`.
- Puede tener valores asociados a muchos productos mediante `GlobalProductAttributeValue`.

---

## 4.3.2 GlobalBrand

**Tabla:** `global_brands`

**Naturaleza:** global y compartida.

**Servicio propietario:** Product Catalog Service.

### Descripción

Representa una marca global normalizada que puede estar asociada a múltiples productos dentro de SIO.

Permite evitar que la marca se almacene como texto libre directamente en `GlobalProduct`, reduciendo duplicados semánticos como `TECNOQUIMICAS`, `Tecnoquímicas` o `TECNO QUIMICAS`.

La marca representa una identidad comercial global del producto y no contiene configuraciones privadas de una empresa, precios, costos, inventario ni condiciones comerciales.

Una marca utilizada históricamente no debe eliminarse físicamente. Cuando deje de estar disponible para nuevos productos debe cambiarse a estado `INACTIVE`.

### Atributos

| Atributo      | Tipo           | Regla           | Descripción                                      |
| ------------- | -------------- | --------------- | ------------------------------------------------ |
| `id`          | `UUID`         | PK, NN          | Identificador global de la marca.                |
| `code`        | `VARCHAR(50)`  | NN, UQ          | Código estable y normalizado de la marca.        |
| `name`        | `VARCHAR(120)` | NN              | Nombre oficial de la marca.                      |
| `description` | `TEXT`         | nullable        | Descripción o información adicional de la marca. |
| `status`      | `VARCHAR(20)`  | NN, CK          | Estado `ACTIVE` o `INACTIVE`.                    |
| `version`     | `INTEGER`      | NN, DEFAULT `1` | Control de concurrencia y cambios.               |
| `created_at`  | `TIMESTAMPTZ`  | NN              | Fecha de creación.                               |
| `updated_at`  | `TIMESTAMPTZ`  | NN              | Última modificación.                             |

### Reglas y restricciones

- `code` debe ser único globalmente sin diferenciar mayúsculas y minúsculas.
- `name` debe contener un valor significativo después de normalización.
- Una marca `INACTIVE` no puede asignarse a productos nuevos.
- Una marca utilizada históricamente no debe eliminarse físicamente.
- La desactivación de una marca no modifica automáticamente los productos históricos que ya la utilizan.
- La marca no reemplaza el fabricante del producto; marca y fabricante representan conceptos diferentes.

### Relaciones

- Puede estar asociada a múltiples `GlobalProduct`.
- Un `GlobalProduct` puede tener una marca principal mediante `global_brand_id`.
- No tiene relación directa con `CompanyProduct`, ya que la marca pertenece a la definición global del producto.

---

## 4.3.3 GlobalProductCategory

**Tabla:** `global_product_categories`

**Naturaleza:** global y compartida.

**Servicio propietario:** Product Catalog Service.

### Descripción

Representa la relación entre un producto global y una categoría global.

Permite que un mismo `GlobalProduct` pertenezca simultáneamente a múltiples categorías, eliminando la limitación anterior donde `GlobalProduct.global_category_id` permitía únicamente una categoría.

Una de las categorías puede marcarse como principal para búsquedas, presentación o compatibilidad con procesos que requieran una clasificación predeterminada, pero las demás categorías continúan siendo clasificaciones válidas del producto.

La entidad permite conservar el historial lógico de las asociaciones mediante `is_active` sin eliminar físicamente relaciones que hayan sido utilizadas.

### Atributos

| Atributo             | Tipo          | Regla               | Descripción                                       |
| -------------------- | ------------- | ------------------- | ------------------------------------------------- |
| `id`                 | `UUID`        | PK, NN              | Identificador de la relación.                     |
| `global_product_id`  | `UUID`        | FK, NN              | Producto global clasificado.                      |
| `global_category_id` | `UUID`        | FK, NN              | Categoría global asignada.                        |
| `is_primary`         | `BOOLEAN`     | NN, DEFAULT `FALSE` | Indica si es la categoría principal del producto. |
| `is_active`          | `BOOLEAN`     | NN, DEFAULT `TRUE`  | Indica si la clasificación está vigente.          |
| `created_at`         | `TIMESTAMPTZ` | NN                  | Fecha de creación.                                |
| `updated_at`         | `TIMESTAMPTZ` | NN                  | Última modificación.                              |

### Reglas y restricciones

- La combinación `global_product_id` y `global_category_id` es única.
- Un producto debe tener al menos una categoría activa antes de considerarse completamente clasificado.
- Un producto puede tener múltiples categorías activas.
- Un producto puede tener como máximo una categoría principal activa.
- Debe existir un índice único parcial sobre `global_product_id` cuando `is_primary = TRUE` e `is_active = TRUE`.
- Una categoría `INACTIVE` no puede asignarse a productos nuevos.
- Una asociación utilizada históricamente no debe eliminarse físicamente; debe cambiarse a `is_active = FALSE`.
- Cambiar la categoría principal no elimina las otras clasificaciones del producto.
- Los atributos obligatorios definidos por las categorías activas deben considerarse durante la validación del producto.

### Relaciones

- Pertenece a un `GlobalProduct` mediante `global_product_id`.
- Pertenece a una `GlobalCategory` mediante `global_category_id`.
- Permite una relación N:M entre `GlobalProduct` y `GlobalCategory`.
- Las categorías asociadas participan en la validación de `GlobalCategoryAttribute`.

---

## 4.3.4 GlobalPackagingType

**Tabla:** `global_packaging_types`

**Naturaleza:** global y compartida.

**Servicio propietario:** Product Catalog Service.

### Descripción

Representa tipos globales de empaque o presentación física utilizados para describir cómo se encuentra contenido o presentado un producto.

Permite diferenciar conceptos de empaque como `CAJA`, `FRASCO`, `TUBO`, `BOLSA`, `PAQUETE`, `LATA` o `BLISTER` de unidades de medida como `KG`, `G`, `ML` o `L`.

No representa una cantidad ni realiza conversiones por sí misma. La composición física de una presentación se define mediante `GlobalProductPresentation`.

### Atributos

| Atributo      | Tipo           | Regla           | Descripción                                       |
| ------------- | -------------- | --------------- | ------------------------------------------------- |
| `id`          | `UUID`         | PK, NN          | Identificador global.                             |
| `code`        | `VARCHAR(50)`  | NN, UQ          | Código estable y normalizado del tipo de empaque. |
| `name`        | `VARCHAR(120)` | NN              | Nombre visible del tipo de empaque.               |
| `description` | `TEXT`         | nullable        | Descripción o criterios de utilización.           |
| `status`      | `VARCHAR(20)`  | NN, CK          | Estado `ACTIVE` o `INACTIVE`.                     |
| `version`     | `INTEGER`      | NN, DEFAULT `1` | Control de concurrencia.                          |
| `created_at`  | `TIMESTAMPTZ`  | NN              | Fecha de creación.                                |
| `updated_at`  | `TIMESTAMPTZ`  | NN              | Última modificación.                              |

### Reglas y restricciones

- `code` debe ser único globalmente sin diferenciar mayúsculas y minúsculas.
- Un tipo de empaque `INACTIVE` no puede asignarse a presentaciones nuevas.
- Un tipo de empaque utilizado históricamente no debe eliminarse físicamente.
- Los tipos de empaque no deben duplicar unidades de medida.
- Conceptos como `BOX`, `BOTTLE`, `TUBE`, `BAG`, `PACK`, `CAN`, `JAR`, `ENVELOPE`, `ROLL` o `BLISTER` pertenecen a esta entidad.
- Magnitudes como `KG`, `G`, `ML`, `L`, `M` o `CM` continúan perteneciendo a `GlobalUnitOfMeasure`.

### Relaciones

- Puede ser utilizado por múltiples `GlobalProductPresentation`.
- No se relaciona directamente con `GlobalProduct`; la relación se establece mediante la presentación.

---

## 4.3.5 GlobalProductPresentation

**Tabla:** `global_product_presentations`

**Naturaleza:** global y compartida.

**Servicio propietario:** Product Catalog Service.

### Descripción

Representa una presentación física global de un producto.

Permite describir casos como `UNIDAD`, `BLISTER X 10 TABLETAS`, `CAJA X 20 TABLETAS`, `FRASCO X 120 ML` o `TUBO X 15 G` sin crear productos globales duplicados cuando la identidad comercial corresponde al mismo producto.

La entidad define las características físicas de la presentación y su equivalencia con la unidad base del producto.

No almacena precio, costo, SKU privado, disponibilidad de compra o disponibilidad de venta, ya que esas configuraciones pertenecen a `CompanyProductPresentation`.

### Atributos

| Atributo            | Tipo            | Regla               | Descripción                                                |
| ------------------- | --------------- | ------------------- | ---------------------------------------------------------- |
| `id`                | `UUID`          | PK, NN              | Identificador global de la presentación.                   |
| `global_product_id` | `UUID`          | FK, NN              | Producto global al que pertenece.                          |
| `code`              | `VARCHAR(60)`   | NN                  | Código estable de la presentación dentro del producto.     |
| `name`              | `VARCHAR(160)`  | NN                  | Nombre visible de la presentación.                         |
| `packaging_type_id` | `UUID`          | FK, nullable        | Tipo de empaque utilizado.                                 |
| `base_quantity`     | `NUMERIC(18,8)` | NN, DEFAULT `1`     | Cantidad de unidades base equivalentes a una presentación. |
| `content_quantity`  | `NUMERIC(18,4)` | nullable            | Cantidad física declarada del contenido.                   |
| `content_unit_id`   | `UUID`          | FK, nullable        | Unidad global utilizada para expresar el contenido.        |
| `display_order`     | `SMALLINT`      | NN, DEFAULT `0`     | Orden sugerido de visualización.                           |
| `is_base`           | `BOOLEAN`       | NN, DEFAULT `FALSE` | Indica si es la presentación base del producto.            |
| `status`            | `VARCHAR(20)`   | NN, CK              | Estado `ACTIVE` o `INACTIVE`.                              |
| `version`           | `INTEGER`       | NN, DEFAULT `1`     | Control concurrente.                                       |
| `created_at`        | `TIMESTAMPTZ`   | NN                  | Fecha de creación.                                         |
| `updated_at`        | `TIMESTAMPTZ`   | NN                  | Última modificación.                                       |

### Reglas y restricciones

- La combinación `global_product_id` y `code` debe ser única.
- `base_quantity` debe ser mayor que cero.
- `content_quantity` debe ser mayor que cero cuando exista.
- Cuando exista `content_quantity`, debe existir `content_unit_id`.
- `display_order` no puede ser negativo.
- Un producto puede tener múltiples presentaciones.
- Un producto puede tener como máximo una presentación base activa.
- Para la presentación marcada como `is_base = TRUE`, normalmente `base_quantity` debe ser `1`.
- `base_quantity` se interpreta respecto de `GlobalProduct.base_unit_id`.
- Una presentación `INACTIVE` no puede utilizarse para nuevas adopciones empresariales.
- Una presentación utilizada históricamente no debe eliminarse físicamente.

### Relaciones

- Pertenece a un `GlobalProduct` mediante `global_product_id`.
- Puede utilizar un `GlobalPackagingType` mediante `packaging_type_id`.
- Puede utilizar una `GlobalUnitOfMeasure` mediante `content_unit_id`.
- Puede tener múltiples identificadores mediante `GlobalProductIdentifier`.
- Puede ser adoptada por empresas mediante `CompanyProductPresentation`.

---

## 4.3.6 GlobalProductIdentifier

**Tabla:** `global_product_identifiers`

**Naturaleza:** global y compartida.

**Servicio propietario:** Product Catalog Service.

### Descripción

Representa los identificadores externos asociados a un producto global o a una presentación específica.

Permite que un producto tenga múltiples códigos de barras u otros identificadores sin limitar el modelo a los campos fijos `gtin` y `barcode`.

Esta entidad permite representar los campos `Código Barras 1`, `Código Barras 2` y `Código Barras 3` encontrados en fuentes externas como registros independientes.

### Atributos

| Atributo                         | Tipo           | Regla               | Descripción                                                    |
| -------------------------------- | -------------- | ------------------- | -------------------------------------------------------------- |
| `id`                             | `UUID`         | PK, NN              | Identificador global.                                          |
| `global_product_id`              | `UUID`         | FK, NN              | Producto global identificado.                                  |
| `global_product_presentation_id` | `UUID`         | FK, nullable        | Presentación específica cuando el código pertenece a ella.     |
| `identifier_type`                | `VARCHAR(30)`  | NN, CK              | Tipo del identificador.                                        |
| `value`                          | `VARCHAR(100)` | NN                  | Valor normalizado del identificador.                           |
| `is_primary`                     | `BOOLEAN`      | NN, DEFAULT `FALSE` | Indica si es el identificador principal dentro de su contexto. |
| `status`                         | `VARCHAR(20)`  | NN, CK              | Estado `ACTIVE` o `INACTIVE`.                                  |
| `created_at`                     | `TIMESTAMPTZ`  | NN                  | Fecha de creación.                                             |
| `updated_at`                     | `TIMESTAMPTZ`  | NN                  | Última modificación.                                           |

### Reglas y restricciones

- `identifier_type` admite inicialmente `GTIN`, `EAN`, `UPC`, `BARCODE` u `OTHER`.
- Cuando exista `global_product_presentation_id`, la presentación debe pertenecer al mismo `global_product_id`.
- Los identificadores destinados a identificación inequívoca o lectura automática deben ser únicos después de normalización.
- Una colisión entre códigos durante una importación debe tratarse como inconsistencia y no resolverse automáticamente.
- Puede existir como máximo un identificador principal activo por tipo y contexto.
- Los identificadores utilizados históricamente no deben eliminarse físicamente.
- Un identificador `INACTIVE` no debe aceptarse como código vigente para nuevas operaciones.
- Los códigos deben almacenarse como texto y no como números para conservar ceros iniciales.

### Relaciones

- Pertenece a un `GlobalProduct`.
- Puede pertenecer a una `GlobalProductPresentation`.
- Un producto puede tener múltiples identificadores.
- Una presentación puede tener múltiples identificadores.

---

## 4.3.7 GlobalProductGroupType

**Tabla:** `global_product_group_types`

**Naturaleza:** global y compartida.

**Servicio propietario:** Product Catalog Service.

### Descripción

Representa una dimensión global utilizada para clasificar productos mediante grupos adicionales a las categorías.

Permite soportar de forma normalizada los grupos encontrados en fuentes externas, como `Grupo 1` hasta `Grupo 15`, sin crear quince columnas permanentes en `GlobalProduct`.

También permite incorporar en el futuro otras dimensiones globales como tipo comercial, colección o clasificación sin modificar la estructura de la tabla de productos.

### Atributos

| Atributo          | Tipo           | Regla               | Descripción                                                      |
| ----------------- | -------------- | ------------------- | ---------------------------------------------------------------- |
| `id`              | `UUID`         | PK, NN              | Identificador global.                                            |
| `code`            | `VARCHAR(50)`  | NN, UQ              | Código estable del tipo de grupo.                                |
| `name`            | `VARCHAR(120)` | NN                  | Nombre visible.                                                  |
| `description`     | `TEXT`         | nullable            | Explica el propósito de la dimensión.                            |
| `allows_multiple` | `BOOLEAN`      | NN, DEFAULT `FALSE` | Indica si un producto puede tener varios valores del mismo tipo. |
| `display_order`   | `SMALLINT`     | NN, DEFAULT `0`     | Orden sugerido de presentación.                                  |
| `status`          | `VARCHAR(20)`  | NN, CK              | Estado `ACTIVE` o `INACTIVE`.                                    |
| `version`         | `INTEGER`      | NN, DEFAULT `1`     | Control concurrente.                                             |
| `created_at`      | `TIMESTAMPTZ`  | NN                  | Fecha de creación.                                               |
| `updated_at`      | `TIMESTAMPTZ`  | NN                  | Última modificación.                                             |

### Reglas y restricciones

- `code` debe ser único globalmente.
- `display_order` no puede ser negativo.
- Un tipo de grupo `INACTIVE` no puede recibir nuevas clasificaciones.
- `allows_multiple = FALSE` significa que un producto solo puede tener un grupo activo perteneciente a ese tipo.
- Los tipos utilizados históricamente no deben eliminarse físicamente.
- Para el caso inicial deben poder definirse `GROUP_1` hasta `GROUP_15`.
- El mecanismo debe permitir nuevos tipos sin modificar el esquema de `GlobalProduct`.

### Relaciones

- Puede tener múltiples `GlobalProductGroup`.
- Sus valores se asignan a productos mediante `GlobalProductGroupAssignment`.

---

## 4.3.8 GlobalProductGroup

**Tabla:** `global_product_groups`

**Naturaleza:** global y compartida.

**Servicio propietario:** Product Catalog Service.

### Descripción

Representa un valor concreto perteneciente a una dimensión definida mediante `GlobalProductGroupType`.

Por ejemplo, si existe el tipo `GROUP_1`, esta entidad puede contener valores como `MEDICAMENTOS`, `ALIMENTOS` o cualquier clasificación global aprobada.

Permite opcionalmente relaciones jerárquicas entre grupos pertenecientes al mismo tipo, aunque la existencia de una jerarquía no debe asumirse para los grupos importados.

### Atributos

| Atributo          | Tipo           | Regla           | Descripción                                 |
| ----------------- | -------------- | --------------- | ------------------------------------------- |
| `id`              | `UUID`         | PK, NN          | Identificador global del grupo.             |
| `group_type_id`   | `UUID`         | FK, NN          | Tipo de clasificación a la que pertenece.   |
| `parent_group_id` | `UUID`         | FK, nullable    | Grupo superior cuando exista jerarquía.     |
| `code`            | `VARCHAR(50)`  | NN              | Código estable del grupo dentro de su tipo. |
| `name`            | `VARCHAR(160)` | NN              | Nombre visible.                             |
| `description`     | `TEXT`         | nullable        | Descripción del grupo.                      |
| `status`          | `VARCHAR(20)`  | NN, CK          | Estado `ACTIVE` o `INACTIVE`.               |
| `version`         | `INTEGER`      | NN, DEFAULT `1` | Control concurrente.                        |
| `created_at`      | `TIMESTAMPTZ`  | NN              | Fecha de creación.                          |
| `updated_at`      | `TIMESTAMPTZ`  | NN              | Última modificación.                        |

### Reglas y restricciones

- La combinación `group_type_id` y `code` debe ser única.
- Cuando exista `parent_group_id`, el grupo padre debe pertenecer al mismo `group_type_id`.
- `parent_group_id` no puede apuntar al mismo registro.
- Deben impedirse ciclos jerárquicos.
- No debe asumirse que todos los tipos poseen una estructura jerárquica.
- Un grupo `INACTIVE` no puede asignarse a productos nuevos.
- Un grupo utilizado históricamente no debe eliminarse físicamente.

### Relaciones

- Pertenece a un `GlobalProductGroupType`.
- Puede tener un `GlobalProductGroup` padre.
- Puede tener múltiples grupos hijos.
- Puede asignarse a múltiples productos mediante `GlobalProductGroupAssignment`.

---

## 4.3.9 GlobalProductGroupAssignment

**Tabla:** `global_product_group_assignments`

**Naturaleza:** global y compartida.

**Servicio propietario:** Product Catalog Service.

### Descripción

Representa la asignación de una clasificación global a un producto.

Permite que `GlobalProduct` utilice los diferentes grupos definidos mediante `GlobalProductGroup` sin incorporar columnas específicas por cada dimensión de clasificación.

La asociación puede desactivarse manteniendo la trazabilidad histórica de que el producto estuvo clasificado de esa manera.

### Atributos

| Atributo                  | Tipo          | Regla              | Descripción                              |
| ------------------------- | ------------- | ------------------ | ---------------------------------------- |
| `id`                      | `UUID`        | PK, NN             | Identificador de la relación.            |
| `global_product_id`       | `UUID`        | FK, NN             | Producto global clasificado.             |
| `global_product_group_id` | `UUID`        | FK, NN             | Grupo global asignado.                   |
| `is_active`               | `BOOLEAN`     | NN, DEFAULT `TRUE` | Indica si la clasificación está vigente. |
| `created_at`              | `TIMESTAMPTZ` | NN                 | Fecha de creación.                       |
| `updated_at`              | `TIMESTAMPTZ` | NN                 | Última modificación.                     |

### Reglas y restricciones

- La combinación `global_product_id` y `global_product_group_id` debe ser única.
- Solo grupos `ACTIVE` pueden asignarse a productos nuevos.
- Cuando `GlobalProductGroupType.allows_multiple = FALSE`, un producto puede tener como máximo un grupo activo perteneciente a ese tipo.
- Una clasificación utilizada históricamente no debe eliminarse físicamente; debe cambiarse a `is_active = FALSE`.
- La clasificación mediante grupos no reemplaza las categorías globales.
- Categorías y grupos pueden coexistir en un mismo producto porque representan mecanismos de clasificación diferentes.

### Relaciones

- Pertenece a un `GlobalProduct`.
- Pertenece a un `GlobalProductGroup`.
- El tipo de clasificación se obtiene mediante `GlobalProductGroup.group_type_id`.

---

## 4.3.10 ProductAttributeOption

**Tabla:** `product_attribute_options`

**Naturaleza:** global y compartida.

**Servicio propietario:** Product Catalog Service.

### Descripción

Representa una opción controlada que puede utilizarse como valor para un atributo global de tipo `OPTION`.

Permite definir catálogos de valores reutilizables como colores, tallas u otras características discretas evitando almacenar variaciones del mismo concepto como texto libre.

Por ejemplo, una definición `COLOR` puede tener opciones `RED`, `BLUE`, `BLACK` y `WHITE`, mientras que `SIZE` puede tener `XS`, `S`, `M`, `L` y `XL`.

### Atributos

| Atributo                  | Tipo           | Regla           | Descripción                               |
| ------------------------- | -------------- | --------------- | ----------------------------------------- |
| `id`                      | `UUID`         | PK, NN          | Identificador global de la opción.        |
| `attribute_definition_id` | `UUID`         | FK, NN          | Definición del atributo al que pertenece. |
| `code`                    | `VARCHAR(80)`  | NN              | Código estable de la opción.              |
| `name`                    | `VARCHAR(120)` | NN              | Nombre visible.                           |
| `description`             | `TEXT`         | nullable        | Descripción opcional.                     |
| `display_order`           | `SMALLINT`     | NN, DEFAULT `0` | Orden sugerido de presentación.           |
| `status`                  | `VARCHAR(20)`  | NN, CK          | Estado `ACTIVE` o `INACTIVE`.             |
| `version`                 | `INTEGER`      | NN, DEFAULT `1` | Control concurrente.                      |
| `created_at`              | `TIMESTAMPTZ`  | NN              | Fecha de creación.                        |
| `updated_at`              | `TIMESTAMPTZ`  | NN              | Última modificación.                      |

### Reglas y restricciones

- La combinación `attribute_definition_id` y `code` debe ser única.
- La definición asociada debe utilizar `data_type = OPTION`.
- `display_order` no puede ser negativo.
- Una opción `INACTIVE` no puede asignarse a productos nuevos.
- Una opción utilizada históricamente no debe eliminarse físicamente.
- Las opciones pertenecen exclusivamente a su `ProductAttributeDefinition`.
- Una opción de `COLOR`, por ejemplo, no puede utilizarse como valor de un atributo `SIZE`.

### Relaciones

- Pertenece a una `ProductAttributeDefinition`.
- Puede ser utilizada por múltiples `GlobalProductAttributeValue`.
- Su utilización requiere agregar `OPTION` a los tipos permitidos de `ProductAttributeDefinition`.

---

## 4.3.11 GlobalCategoryAttribute

**Tabla:** `global_category_attributes`
**Naturaleza:** global y compartida.
**Servicio propietario:** Product Catalog Service.

### Descripción

Representa la relación entre una categoría global y los atributos que pueden utilizar los productos pertenecientes a esa categoría.

Permite que una categoría tenga múltiples características y que una misma definición de atributo pueda reutilizarse en diferentes categorías sin duplicarse.

La entidad también permite determinar si un atributo es obligatorio para una categoría, si puede utilizarse como criterio de búsqueda o filtrado y en qué orden debe mostrarse.

No almacena el valor concreto del atributo para un producto; esos valores pertenecen a `GlobalProductAttributeValue`.

### Atributos

| Atributo                  | Tipo          | Regla               | Descripción                                                    |
| ------------------------- | ------------- | ------------------- | -------------------------------------------------------------- |
| `id`                      | `UUID`        | PK, NN              | Identificador de la relación.                                  |
| `global_category_id`      | `UUID`        | FK, NN              | Categoría global a la que se asigna el atributo.               |
| `attribute_definition_id` | `UUID`        | FK, NN              | Definición global del atributo permitido para la categoría.    |
| `is_required`             | `BOOLEAN`     | NN, DEFAULT `FALSE` | Indica si el atributo es obligatorio para los productos.       |
| `is_filterable`           | `BOOLEAN`     | NN, DEFAULT `FALSE` | Indica si puede utilizarse como filtro o criterio de búsqueda. |
| `display_order`           | `SMALLINT`    | NN, DEFAULT `0`     | Orden sugerido para mostrar el atributo.                       |
| `is_active`               | `BOOLEAN`     | NN, DEFAULT `TRUE`  | Indica si la relación categoría-atributo está vigente.         |
| `created_at`              | `TIMESTAMPTZ` | NN                  | Fecha de creación.                                             |
| `updated_at`              | `TIMESTAMPTZ` | NN                  | Última modificación.                                           |

### Reglas y restricciones

- La combinación `global_category_id` y `attribute_definition_id` es única.
- Una categoría puede tener muchos atributos asociados.
- Una misma definición de atributo puede utilizarse en muchas categorías.
- La categoría y la definición del atributo deben estar activas para crear una nueva relación.
- `display_order` no puede ser negativo.
- Una relación utilizada históricamente no debe eliminarse físicamente; debe cambiarse a `is_active = FALSE`.

### Relaciones

- Pertenece a una `GlobalCategory` mediante `global_category_id`.
- Utiliza una `ProductAttributeDefinition` mediante `attribute_definition_id`.
- Define qué atributos pueden utilizarse posteriormente en `GlobalProductAttributeValue`.

---

## 4.3.12 GlobalProductAttributeValue

**Tabla:** `global_product_attribute_values`
**Naturaleza:** global y compartida.
**Servicio propietario:** Product Catalog Service.

### Descripción

Almacena el valor concreto de una característica global para un producto determinado.

`ProductAttributeDefinition` determina qué significa el atributo y qué tipo de dato acepta mientras `GlobalProductAttributeValue` registra el valor que corresponde específicamente a un `GlobalProduct`.

Los valores permanecen en el catálogo global porque representan características propias del producto y no configuraciones comerciales privadas de una empresa.

No debe almacenar precios, costos, inventario, códigos internos ni información específica de una empresa.

### Atributos

| Atributo                  | Tipo            | Regla        | Descripción                                                          |
| ------------------------- | --------------- | ------------ | -------------------------------------------------------------------- |
| `id`                      | `UUID`          | PK, NN       | Identificador global del valor.                                      |
| `global_product_id`       | `UUID`          | FK, NN       | Producto global al que pertenece la característica.                  |
| `attribute_definition_id` | `UUID`          | FK, NN       | Definición del atributo cuyo valor se almacena.                      |
| `option_id`               | `UUID`          | FK, nullable | Opción seleccionada cuando el atributo utiliza `data_type = OPTION`. |
| `text_value`              | `TEXT`          | nullable     | Valor cuando el atributo es de tipo `TEXT`.                          |
| `integer_value`           | `BIGINT`        | nullable     | Valor cuando el atributo es de tipo `INTEGER`.                       |
| `decimal_value`           | `NUMERIC(18,8)` | nullable     | Valor cuando el atributo es de tipo `DECIMAL`.                       |
| `boolean_value`           | `BOOLEAN`       | nullable     | Valor cuando el atributo es de tipo `BOOLEAN`.                       |
| `date_value`              | `DATE`          | nullable     | Valor cuando el atributo es de tipo `DATE`.                          |
| `created_at`              | `TIMESTAMPTZ`   | NN           | Fecha de creación.                                                   |
| `updated_at`              | `TIMESTAMPTZ`   | NN           | Última modificación.                                                 |

### Reglas y restricciones

- La combinación `global_product_id` y `attribute_definition_id` es única.
- Cada producto puede tener como máximo un valor vigente para una misma definición de atributo.
- Exactamente uno de los campos `option_id`, `text_value`, `integer_value`, `decimal_value`, `boolean_value` o `date_value` debe contener un valor.
- El campo utilizado debe corresponder al `data_type` establecido en `ProductAttributeDefinition`.
- Cuando `ProductAttributeDefinition.data_type = OPTION`, debe utilizarse exclusivamente `option_id`.
- La opción seleccionada mediante `option_id` debe pertenecer a la misma `ProductAttributeDefinition` indicada por `attribute_definition_id`.
- Un atributo solo puede asignarse al producto cuando esté activo y sea permitido por al menos una categoría activa asociada al producto mediante `GlobalProductCategory`.
- Los valores deben cumplir las validaciones propias de su definición.
- No se deben almacenar valores como texto cuando exista un tipo estructurado apropiado.
- Los valores pertenecen al producto global y no deben contener información comercial privada de una empresa.

### Relaciones

- Pertenece a un `GlobalProduct`.
- Utiliza una definición de `ProductAttributeDefinition`.
- Puede utilizar una `ProductAttributeOption` cuando la definición sea de tipo `OPTION`.
- La validez del atributo se determina mediante las categorías activas del producto en `GlobalProductCategory` y las reglas de `GlobalCategoryAttribute`.

## 4.3.13 ProductAsset

**Tabla:** `product_assets`  
**Naturaleza:** global y compartida.  
**Servicio propietario:** Product Catalog Service.

### Descripción

Representa los archivos y recursos asociados con un producto global, como imágenes, fichas técnicas, manuales o certificados.

PostgreSQL conserva únicamente la referencia al recurso y sus metadatos.

El contenido binario debe almacenarse en un servicio de objetos o repositorio documental.

Permite que un producto tenga múltiples activos sin limitar el diseño a una única URL.

### Atributos

| Atributo            | Tipo           | Regla               | Descripción                                                    |
| ------------------- | -------------- | ------------------- | -------------------------------------------------------------- |
| `id`                | `UUID`         | PK, NN              | Identificador del activo.                                      |
| `global_product_id` | `UUID`         | FK, NN              | Producto global asociado.                                      |
| `asset_type`        | `VARCHAR(30)`  | NN, CK              | `IMAGE`, `TECHNICAL_SHEET`, `MANUAL`, `CERTIFICATE` u `OTHER`. |
| `file_name`         | `VARCHAR(255)` | NN                  | Nombre lógico del archivo.                                     |
| `storage_uri`       | `TEXT`         | NN                  | Referencia al recurso almacenado externamente.                 |
| `mime_type`         | `VARCHAR(120)` | nullable            | Tipo MIME conocido.                                            |
| `is_primary`        | `BOOLEAN`      | NN, DEFAULT `FALSE` | Indica el activo principal de su tipo.                         |
| `version`           | `INTEGER`      | NN, DEFAULT `1`     | Control concurrente.                                           |
| `created_at`        | `TIMESTAMPTZ`  | NN                  | Creación.                                                      |
| `updated_at`        | `TIMESTAMPTZ`  | NN                  | Modificación.                                                  |

### Reglas y restricciones

- Un producto puede tener múltiples activos.
- Debe existir como máximo un activo principal por producto y `asset_type` cuando el tipo requiera principal.
- La eliminación del archivo físico debe estar coordinada con la vigencia del registro.
- No se almacenan binarios en la tabla.

### Relaciones

- Pertenece a un único `GlobalProduct`.

## 4.4 GlobalCountry

**Tabla:** `global_countries`  
**Naturaleza:** catálogo maestro global.  
**Servicio propietario:** Geography Service.

### Descripción

Representa los países utilizados por SIO para direcciones, documentos de identidad, organizaciones, empresas y sucursales.

Evita registrar variantes libres como `Colombia`, `COLOMBIA`, `COL` o `Col.` y permite utilizar códigos internacionales estables.

### Atributos

| Atributo       | Tipo           | Regla           | Descripción                                   |
| -------------- | -------------- | --------------- | --------------------------------------------- |
| `id`           | `UUID`         | PK, NN          | Identificador global.                         |
| `iso2_code`    | `CHAR(2)`      | NN, UQ          | Código ISO 3166-1 alpha-2, por ejemplo `CO`.  |
| `iso3_code`    | `CHAR(3)`      | NN, UQ          | Código ISO 3166-1 alpha-3, por ejemplo `COL`. |
| `name`         | `VARCHAR(120)` | NN              | Nombre oficial utilizado por SIO.             |
| `phone_prefix` | `VARCHAR(10)`  | nullable        | Prefijo telefónico internacional.             |
| `status`       | `VARCHAR(20)`  | NN, CK          | `ACTIVE` o `INACTIVE`.                        |
| `version`      | `INTEGER`      | NN, DEFAULT `1` | Control concurrente.                          |
| `created_at`   | `TIMESTAMPTZ`  | NN              | Creación.                                     |
| `updated_at`   | `TIMESTAMPTZ`  | NN              | Modificación.                                 |

### Reglas y restricciones

- `iso2_code` e `iso3_code` son únicos sin diferenciar mayúsculas y minúsculas.
- Un país utilizado históricamente no se elimina físicamente.
- Los registros inactivos no pueden asignarse a nuevas direcciones.

## 4.5 GlobalAdministrativeDivision

**Tabla:** `global_administrative_divisions`  
**Naturaleza:** catálogo maestro global y jerárquico.  
**Servicio propietario:** Geography Service.

### Descripción

Representa departamentos, estados, provincias, regiones, distritos u otras divisiones administrativas de un país.

El modelo evita asumir que todos los países utilizan la misma estructura territorial.

### Atributos

| Atributo             | Tipo           | Regla           | Descripción                                                        |
| -------------------- | -------------- | --------------- | ------------------------------------------------------------------ |
| `id`                 | `UUID`         | PK, NN          | Identificador global.                                              |
| `country_id`         | `UUID`         | FK, NN          | País al que pertenece.                                             |
| `parent_division_id` | `UUID`         | FK, nullable    | División administrativa superior cuando exista.                    |
| `code`               | `VARCHAR(40)`  | NN              | Código oficial o interno gobernado.                                |
| `name`               | `VARCHAR(160)` | NN              | Nombre de la división.                                             |
| `division_type`      | `VARCHAR(30)`  | NN, CK          | `DEPARTMENT`, `STATE`, `PROVINCE`, `REGION`, `DISTRICT` u `OTHER`. |
| `status`             | `VARCHAR(20)`  | NN, CK          | `ACTIVE` o `INACTIVE`.                                             |
| `version`            | `INTEGER`      | NN, DEFAULT `1` | Control concurrente.                                               |
| `created_at`         | `TIMESTAMPTZ`  | NN              | Creación.                                                          |
| `updated_at`         | `TIMESTAMPTZ`  | NN              | Modificación.                                                      |

### Reglas y restricciones

- `code` es único dentro de un país y su nivel administrativo aplicable.
- `parent_division_id` debe pertenecer al mismo país.
- Se deben impedir ciclos jerárquicos.
- Una división utilizada históricamente no se elimina físicamente.

## 4.6 GlobalCity

**Tabla:** `global_cities`  
**Naturaleza:** catálogo maestro global.  
**Servicio propietario:** Geography Service.

### Descripción

Sirve para evitar guardar la ciudad como texto libre en cada empresa, sucursal, proveedor o cliente y tener una única referencia oficial de cada ciudad dentro de SIO

Representa ciudades, municipios o localidades utilizadas en direcciones estructuradas.

Las coordenadas de esta entidad son opcionales y representan un centroide o punto de referencia de la ciudad y no reemplazan las coordenadas exactas de una empresa o sucursal.

### Atributos

| Atributo                     | Tipo           | Regla           | Descripción                        |
| ---------------------------- | -------------- | --------------- | ---------------------------------- |
| `id`                         | `UUID`         | PK, NN          | Identificador global.              |
| `country_id`                 | `UUID`         | FK, NN          | País.                              |
| `administrative_division_id` | `UUID`         | FK, nullable    | División administrativa principal. |
| `code`                       | `VARCHAR(40)`  | nullable        | Código oficial cuando exista.      |
| `name`                       | `VARCHAR(160)` | NN              | Nombre oficial.                    |
| `latitude`                   | `NUMERIC(9,6)` | nullable        | Latitud aproximada del centroide.  |
| `longitude`                  | `NUMERIC(9,6)` | nullable        | Longitud aproximada del centroide. |
| `status`                     | `VARCHAR(20)`  | NN, CK          | `ACTIVE` o `INACTIVE`.             |
| `version`                    | `INTEGER`      | NN, DEFAULT `1` | Control concurrente.               |
| `created_at`                 | `TIMESTAMPTZ`  | NN              | Creación.                          |
| `updated_at`                 | `TIMESTAMPTZ`  | NN              | Modificación.                      |

### Reglas y restricciones

- La ciudad debe pertenecer al mismo país que su división administrativa.
- Si existe una coordenada debe existir la otra.
- `latitude` debe estar entre `-90` y `90` y `longitude` entre `-180` y `180`.
- Las coordenadas de ciudad no deben utilizarse como sustituto de la ubicación exacta de `Company` o `Branch`.

## 4.7 GlobalBusinessSector

**Tabla:** `global_business_sectors`  
**Naturaleza:** catálogo maestro global y jerárquico.  
**Servicio propietario:** Party Identity Service.

### Descripción

Su objetivo es clasificar de forma estandarizada a una organización según el tipo de actividad que desarrolla, no describe a una empresa específica pero si describe el sector al que esa empresa puede pertenecer.

Puede utilizar una clasificación oficial como CIIU u otra taxonomía adoptada por SIO sin almacenar el sector como texto libre.

La jerarquía permite representar macrosectores y actividades más específicas.

### Atributos

| Atributo                | Tipo           | Regla           | Descripción                                 |
| ----------------------- | -------------- | --------------- | ------------------------------------------- |
| `id`                    | `UUID`         | PK, NN          | Identificador.                              |
| `parent_sector_id`      | `UUID`         | FK, nullable    | Sector superior.                            |
| `classification_system` | `VARCHAR(30)`  | NN              | Sistema de clasificación.                   |
| `code`                  | `VARCHAR(40)`  | NN              | Código dentro del sistema de clasificación. |
| `name`                  | `VARCHAR(180)` | NN              | Nombre del sector o actividad.              |
| `description`           | `TEXT`         | nullable        | Alcance de la clasificación.                |
| `status`                | `VARCHAR(20)`  | NN, CK          | `ACTIVE` o `INACTIVE`.                      |
| `version`               | `INTEGER`      | NN, DEFAULT `1` | Control concurrente.                        |
| `created_at`            | `TIMESTAMPTZ`  | NN              | Creación.                                   |
| `updated_at`            | `TIMESTAMPTZ`  | NN              | Modificación.                               |

### Reglas y restricciones

- `classification_system + code` es único.
- Se deben impedir ciclos jerárquicos.
- Un sector utilizado históricamente no se elimina físicamente.

## 4.8 GlobalPaymentConditionType

**Tabla:** `global_payment_condition_types`  
**Naturaleza:** catálogo maestro global.  
**Servicio propietario:** Payment Reference Service.

### Descripción

Hace referencia a un catálogo maestro que define bajo qué condición financiera se realiza una compra o una venta.

No representa el medio por el cual se mueve el dinero por ejemplo una venta puede ser de contado o pagarse parcialmente con efectivo y parcialmente con tarjeta.

### Atributos

| Atributo      | Tipo           | Regla    | Descripción                                                  |
| ------------- | -------------- | -------- | ------------------------------------------------------------ |
| `id`          | `UUID`         | PK, NN   | Identificador.                                               |
| `code`        | `VARCHAR(30)`  | NN, UQ   | Código estable, inicialmente `CASH`, `CREDIT` o `FINANCING`. |
| `name`        | `VARCHAR(100)` | NN       | Nombre visible.                                              |
| `description` | `TEXT`         | nullable | Significado funcional.                                       |
| `status`      | `VARCHAR(20)`  | NN, CK   | `ACTIVE` o `INACTIVE`.                                       |
| `created_by`  | `VARCHAR(255)` | NN       | `sub` del token de quien crea el registro (Constitución D1); inmutable. |
| `updated_by`  | `VARCHAR(255)` | NN       | `sub` del token de quien realizó la última modificación (Constitución D1). |
| `version`     | `INTEGER`      | NN, DEFAULT `1` | Control de concurrencia.                              |
| `created_at`  | `TIMESTAMPTZ`  | NN       | Creación.                                                    |
| `updated_at`  | `TIMESTAMPTZ`  | NN       | Modificación.                                                |

### Reglas y restricciones

- `code` es único e inmutable una vez utilizado.
- `CASH` significa pago exigible de forma inmediata o en la misma fecha de negocio.
- `CREDIT` representa un plazo comercial.
- `FINANCING` representa financiación vinculada a la operación comercial; un préstamo independiente requiere un modelo contractual distinto.
- `status` admite `ACTIVE` e `INACTIVE` (`CHECK`) y solo cambia mediante las acciones explícitas de inactivar y reactivar.
- No existe borrado físico: un tipo de condición que deja de usarse se inactiva (Constitución D7).

> **Reconciliación (2026-10-05):** sección alineada con `specs/008-payment-reference-condition-type-contract`
> (corrección acotada de Payment Reference): se agregan `created_by`/`updated_by` con el `sub` del token
> (Constitución VI y D1) y `version` para la concurrencia optimista (Constitución VII), que la
> implementación ya tenía; el estado cambia solo con acciones explícitas y no hay borrado físico (D7).
> Cierra C-02 / GAP-PR-28 de la feature 008. `GlobalPaymentMethod` (§4.9) no cambia: su corrección
> queda diferida en GAP-PR-18.

## 4.9 GlobalPaymentMethod

**Tabla:** `global_payment_methods`  
**Naturaleza:** catálogo maestro global.  
**Servicio propietario:** Payment Reference Service.

### Descripción

Representa el instrumento utilizado para registrar un pago o recaudo.

Se mantiene separado de la condición de pago. Una operación `CREDIT` puede liquidarse posteriormente mediante transferencia, efectivo u otro medio.

### Atributos

| Atributo             | Tipo           | Regla               | Descripción                                                                                                            |
| -------------------- | -------------- | ------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| `id`                 | `UUID`         | PK, NN              | Identificador.                                                                                                         |
| `code`               | `VARCHAR(40)`  | NN, UQ              | Código estable, por ejemplo `CASH`, `BANK_TRANSFER`, `DEBIT_CARD`, `CREDIT_CARD`, `DIGITAL_WALLET`, `CHECK` u `OTHER`. |
| `name`               | `VARCHAR(120)` | NN                  | Nombre visible.                                                                                                        |
| `method_type`        | `VARCHAR(30)`  | NN, CK              | `CASH`, `BANK`, `CARD`, `WALLET`, `CHECK` u `OTHER`.                                                                   |
| `requires_reference` | `BOOLEAN`      | NN, DEFAULT `FALSE` | Indica si normalmente exige referencia externa.                                                                        |
| `status`             | `VARCHAR(20)`  | NN, CK              | `ACTIVE` o `INACTIVE`.                                                                                                 |
| `created_at`         | `TIMESTAMPTZ`  | NN                  | Creación.                                                                                                              |
| `updated_at`         | `TIMESTAMPTZ`  | NN                  | Modificación.                                                                                                          |

### Reglas y restricciones

- `code` es único e inmutable una vez utilizado.
- Un medio inactivo no puede usarse para pagos nuevos, pero permanece disponible para consulta histórica.

## 4.9.1 IdentificationTypeRule

**Tabla:** `identification_type_rules`  
**Naturaleza:** global, compartida y administrable.  
**Servicio propietario:** Party Identity Service.

### Descripción

Define las reglas de validación aplicables al número de identificación de una persona u organización según el país y el tipo de identificación.

Permite que SIO valide documentos como cédula, pasaporte, documento de extranjero o identificación tributaria sin codificar reglas por país directamente en el código del microservicio.

La entidad no almacena identificaciones reales de personas u organizaciones; solo define el patrón, descripción y ejemplos necesarios para validar `identification_number`.

Cuando no exista una regla activa para una combinación de tipo, país y tipo de identificación, el servicio aplica únicamente validaciones base como obligatoriedad, longitud máxima y unicidad funcional.

### Atributos

| Atributo                     | Tipo           | Regla              | Descripción                                                                  |
| ---------------------------- | -------------- | ------------------ | ---------------------------------------------------------------------------- |
| `id`                         | `UUID`         | PK, NN             | Identificador de la regla.                                                   |
| `party_kind`                 | `VARCHAR(20)`  | NN, CK             | Tipo de parte: `PERSON` u `ORGANIZATION`.                                    |
| `country_id`                 | `UUID`         | REF, NN            | País al que aplica la regla, referencia a Geography Service.                 |
| `identification_type`        | `VARCHAR(40)`  | NN                 | Tipo/formato de identificación al que aplica la regla.                       |
| `sigla`                      | `VARCHAR(10)`  | NN                 | Sigla oficial del documento, por ejemplo `RC`, `TI`, `CC`, `CE` o `NIT`.     |
| `number_pattern`             | `VARCHAR(300)` | NN                 | Expresión regular que debe cumplir el número normalizado.                    |
| `number_pattern_description` | `TEXT`         | NN                 | Mensaje funcional que explica la regla y se puede devolver en errores `422`. |
| `example_value`              | `VARCHAR(40)`  | nullable           | Ejemplo válido del número de identificación.                                 |
| `min_age_years`              | `INTEGER`      | nullable           | Edad mínima permitida para documentos de persona.                            |
| `max_age_years`              | `INTEGER`      | nullable           | Edad máxima permitida para documentos de persona.                            |
| `is_active`                  | `BOOLEAN`      | NN, DEFAULT `TRUE` | Indica si la regla está vigente.                                             |
| `valid_from`                 | `TIMESTAMPTZ`  | NN                 | Inicio de vigencia.                                                          |
| `valid_to`                   | `TIMESTAMPTZ`  | nullable           | Fin de vigencia.                                                             |
| `version`                    | `INTEGER`      | NN, DEFAULT `1`    | Control de concurrencia.                                                     |
| `created_by`                 | `UUID`         | NN                 | Usuario que creó la regla.                                                   |
| `updated_by`                 | `UUID`         | NN                 | Usuario que realizó la última modificación.                                  |
| `created_at`                 | `TIMESTAMPTZ`  | NN                 | Creación.                                                                    |
| `updated_at`                 | `TIMESTAMPTZ`  | NN                 | Modificación.                                                                |

### Reglas y restricciones

- `party_kind` solo permite `PERSON` u `ORGANIZATION`.
- `country_id` es una referencia externa a Geography Service y no utiliza llave foránea física entre bases de datos.
- `country_id` debe existir en Geography Service antes de crear o actualizar reglas.
- `identification_type` identifica el formato específico de documento; no está limitado por un `CHECK` fijo.
- `sigla` es el valor usado por `PersonIdentity.identification_type` para validar personas; no está limitado por un `CHECK` fijo.
- `number_pattern` debe ser una expresión regular válida y no vacía.
- `number_pattern_description` debe explicar la regla de forma entendible para el usuario.
- `min_age_years` y `max_age_years` son opcionales; cuando existan obligan a validar `birth_date` en `PersonIdentity`.
- `max_age_years` debe ser mayor o igual a `min_age_years` cuando ambos existan.
- Debe existir como máximo una regla activa por `party_kind`, `country_id` e `identification_type`.
- Una regla histórica no se elimina físicamente; se desactiva con `is_active = FALSE` y `valid_to` informado.
- `valid_to` debe ser mayor que `valid_from` cuando exista.
- Cambios de patrón que afecten validaciones productivas deben crear una nueva versión histórica de regla.

### Relaciones

- Puede ser utilizada por `PersonIdentity` para validar `identification_number`.
- Puede ser utilizada por `OrganizationIdentity` para validar `identification_number`.
- Referencia un país global mediante `country_id`, sin FK física hacia Geography Service.

### Ejemplos iniciales

Reglas sugeridas para Colombia cuando se configure el `country_id` correspondiente:

| `party_kind` | `identification_type`  | `sigla` | `number_pattern`         | Edad       | Ejemplo       |
| ------------ | ---------------------- | ------- | ------------------------ | ---------- | ------------- |
| `PERSON`     | `CIVIL_REGISTRY`       | `RC`    | `^[0-9]{10}$`            | 0 a 6      | `1000000000`  |
| `PERSON`     | `IDENTITY_CARD_MODERN` | `TI`    | `^[0-9]{10}$`            | 7 a 17     | `1000000000`  |
| `PERSON`     | `CITIZEN_ID_MODERN`    | `CC`    | `^[0-9]{10}$`            | 18+        | `1000000000`  |
| `PERSON`     | `CITIZEN_ID_OLD`       | `CC`    | `^[0-9]{3,8}$`           | 18+        | `12345678`    |
| `PERSON`     | `FOREIGN_CARD`         | `CE`    | `^[0-9]{3,7}$`           | 7+         | `1234567`     |
| `PERSON`     | `TAX_ID`               | `NIT`   | `^[A-Z0-9]{4,11}-[0-9]$` | cualquiera | `900123456-7` |
| `PERSON`     | `IDENTITY_CARD_OLD`    | `TI`    | `^[0-9]{11}$`            | 7 a 17     | `19991234567` |

## 4.10 PersonIdentity

**Tabla:** `person_identities`  
**Naturaleza:** global y compartida con acceso controlado.  
**Servicio propietario:** Party Identity Service.

### Descripción

Representa la identidad global de una persona natural independientemente del rol que desempeñe dentro de SIO.

Una persona puede actuar como cliente, representante legal de una organización u otro rol futuro sin crear identidades diferentes para la misma persona.

La entidad solo responde quién es la persona y no almacena relaciones comerciales, compras, ventas, deuda, preferencias ni roles organizacionales.

### Atributos

| Atributo                    | Tipo           | Regla           | Descripción                                                                       |
| --------------------------- | -------------- | --------------- | --------------------------------------------------------------------------------- |
| `id`                        | `UUID`         | PK, NN          | Identificador global.                                                             |
| `identification_country_id` | `UUID`         | REF, NN         | País emisor o asociado con la identificación, administrado por Geography Service. |
| `identification_type`       | `VARCHAR(40)`  | NN              | Código o sigla de identificación validada contra reglas activas.                  |
| `identification_number`     | `VARCHAR(40)`  | NN              | Número normalizado.                                                               |
| `first_name`                | `VARCHAR(100)` | NN              | Primer nombre.                                                                    |
| `middle_name`               | `VARCHAR(100)` | nullable        | Segundo nombre.                                                                   |
| `last_name`                 | `VARCHAR(100)` | NN              | Primer apellido.                                                                  |
| `second_last_name`          | `VARCHAR(100)` | nullable        | Segundo apellido.                                                                 |
| `birth_date`                | `DATE`         | nullable        | Fecha de nacimiento, dato sensible.                                               |
| `verification_status`       | `VARCHAR(20)`  | NN, CK          | `UNVERIFIED`, `VERIFIED` o `SUSPENDED`.                                           |
| `version`                   | `INTEGER`      | NN, DEFAULT `1` | Control de versión.                                                               |
| `created_at`                | `TIMESTAMPTZ`  | NN              | Creación.                                                                         |
| `updated_at`                | `TIMESTAMPTZ`  | NN              | Modificación.                                                                     |

### Reglas y restricciones

- La combinación país, tipo y número de identificación es única.
- Cuando exista una regla activa en `IdentificationTypeRule` para `PERSON`, país y tipo de identificación, `identification_number` debe cumplir el patrón configurado.
- Si no existe una regla activa, `identification_number` conserva validaciones base: obligatorio, longitud máxima y unicidad funcional.
- La identificación debe enmascararse cuando no sea necesario mostrarla completa.
- No se deben fusionar personas solo por nombre, teléfono o correo.
- Una persona con historia no se elimina físicamente.
- `identification_country_id` es una referencia externa a Geography Service y no utiliza una llave foránea física.
- El país debe existir y encontrarse disponible en Geography Service al crear o modificar una identidad.

### Relaciones

- Puede tener muchas versiones históricas en `PersonContactProfile` con una sola versión activa.
- Puede relacionarse privadamente con empresas como cliente mediante `CompanyCustomer`.
- Puede representar legalmente organizaciones mediante `OrganizationLegalRepresentative`.

## 4.11 PersonContactProfile

**Tabla:** `person_contact_profiles`  
**Naturaleza:** global, compartida, versionada y con acceso controlado.  
**Servicio propietario:** Party Identity Service.

### Descripción

Almacena en una sola fila el correo, teléfono y dirección vigentes de una persona identificada mediante `PersonIdentity`.

La información no se sobrescribe ni se elimina cuando cambia.

La versión vigente se cierra asignando `is_active = FALSE` y `valid_to` se crea una nueva fila activa con el conjunto completo de datos actualizado.

Este comportamiento permite reutilizar los contactos entre empresas, evita registrar repetidamente la misma información y conserva el historial de quién confirmó cada versión y cuándo lo hizo.

### Atributos

| Atributo                     | Tipo           | Regla              | Descripción                                                 |
| ---------------------------- | -------------- | ------------------ | ----------------------------------------------------------- |
| `id`                         | `UUID`         | PK, NN             | Identificador de la versión.                                |
| `person_identity_id`         | `UUID`         | FK, NN             | Persona propietaria del perfil.                             |
| `email`                      | `VARCHAR(254)` | nullable           | Correo.                                                     |
| `phone`                      | `VARCHAR(40)`  | nullable           | Teléfono.                                                   |
| `address_line`               | `TEXT`         | nullable           | Dirección.                                                  |
| `country_id`                 | `UUID`         | REF, nullable      | País administrado por Geography Service.                    |
| `administrative_division_id` | `UUID`         | REF, nullable      | División administrativa administrada por Geography Service. |
| `city_id`                    | `UUID`         | REF, nullable      | Ciudad o municipio administrado por Geography Service.      |
| `postal_code`                | `VARCHAR(20)`  | nullable           | Código postal.                                              |
| `is_active`                  | `BOOLEAN`      | NN, DEFAULT `TRUE` | Versión vigente.                                            |
| `valid_from`                 | `TIMESTAMPTZ`  | NN                 | Inicio de vigencia.                                         |
| `valid_to`                   | `TIMESTAMPTZ`  | nullable           | Fin de vigencia.                                            |
| `confirmed_by_user_id`       | `UUID`         | REF, NN            | Usuario que confirmó.                                       |
| `confirmed_by_company_id`    | `UUID`         | REF, NN            | Empresa desde la cual se confirmó.                          |
| `created_at`                 | `TIMESTAMPTZ`  | NN                 | Creación.                                                   |
| `updated_at`                 | `TIMESTAMPTZ`  | NN                 | Modificación.                                               |

### Reglas y restricciones

- Debe existir como máximo una versión activa por `person_identity_id`.
- Al menos uno de `email`, `phone` o `address_line` debe contener un valor.
- Cuando se informa `city_id` la ciudad debe ser coherente con `administrative_division_id` y `country_id` cuando estos estén presentes.
- Una actualización debe cerrar la versión vigente y crear la nueva versión dentro de una misma transacción.
- Las versiones históricas no se eliminan físicamente.
- `country_id`, `administrative_division_id` y `city_id` son referencias externas a Geography Service y no utilizan llaves foráneas físicas.

## 4.12 OrganizationIdentity

**Tabla:** `organization_identities`  
**Naturaleza:** global y compartida.  
**Servicio propietario:** Party Identity Service.

### Descripción

Representa la identidad legal de una empresa, sociedad, fundación u otra organización.

Puede representar una empresa usuaria de SIO, un proveedor, un cliente empresarial o un fabricante.

Su sector económico y sus representantes legales se administran mediante relaciones específicas y no como texto libre.

No almacena compras, costos, descuentos, crédito, cartera ni evaluaciones privadas.

### Atributos

| Atributo                | Tipo           | Regla           | Descripción                                          |
| ----------------------- | -------------- | --------------- | ---------------------------------------------------- |
| `id`                    | `UUID`         | PK, NN          | Identificador global.                                |
| `country_id`            | `UUID`         | REF, NN         | País de registro administrado por Geography Service. |
| `identification_type`   | `VARCHAR(20)`  | NN              | Tipo de identificación legal.                        |
| `identification_number` | `VARCHAR(40)`  | NN              | Número normalizado.                                  |
| `legal_name`            | `VARCHAR(200)` | NN              | Razón social.                                        |
| `trade_name`            | `VARCHAR(200)` | nullable        | Nombre comercial.                                    |
| `organization_type`     | `VARCHAR(40)`  | nullable        | Tipo jurídico.                                       |
| `registration_status`   | `VARCHAR(30)`  | nullable        | Estado legal conocido.                               |
| `website`               | `VARCHAR(300)` | nullable        | Sitio web corporativo.                               |
| `version`               | `INTEGER`      | NN, DEFAULT `1` | Control de versión.                                  |
| `created_by`            | `UUID`         | NN              | Usuario que creó el registro.                        |
| `updated_by`            | `UUID`         | NN              | Usuario que realizó la última modificación.          |
| `created_at`            | `TIMESTAMPTZ`  | NN              | Creación.                                            |
| `updated_at`            | `TIMESTAMPTZ`  | NN              | Modificación.                                        |

### Reglas y restricciones

- La combinación país, tipo y número de identificación es única.
- `country_id` es una referencia externa a Geography Service y no utiliza llave foránea física entre bases de datos.
- `country_id` debe existir en Geography Service antes de crear o actualizar organizaciones.
- Cuando exista una regla activa en `IdentificationTypeRule` para `ORGANIZATION`, país y sigla de identificación, `identification_number` debe cumplir el patrón configurado.
- Si no existe una regla activa, `identification_number` conserva validaciones base: obligatorio, longitud máxima y unicidad funcional.
- No contiene información comercial privada ni saldos de cartera.
- Una organización con historia no se elimina físicamente.

### Relaciones

- Puede tener versiones históricas de contacto en `OrganizationContactProfile`.
- Puede tener personas de contacto en `OrganizationContactPerson`.
- Puede clasificarse mediante `OrganizationBusinessSector`.
- Puede tener representantes legales versionados en `OrganizationLegalRepresentative`.
- Puede relacionarse con empresas mediante `CompanySupplier` o `CompanyCustomer`.
- Puede aparecer como fabricante de un producto global.

## 4.13 OrganizationContactProfile

**Tabla:** `organization_contact_profiles`  
**Naturaleza:** global, compartida y versionada.  
**Servicio propietario:** Party Identity Service.

### Descripción

Representa la información de contacto principal vigente de una organización dentro del catálogo global de SIO.

La dirección utiliza los catálogos geográficos de SIO y las versiones históricas no se sobrescriben.

### Atributos

| Atributo                     | Tipo           | Regla              | Descripción                                                 |
| ---------------------------- | -------------- | ------------------ | ----------------------------------------------------------- |
| `id`                         | `UUID`         | PK, NN             | Identificador de la versión.                                |
| `organization_identity_id`   | `UUID`         | FK, NN             | Organización.                                               |
| `email`                      | `VARCHAR(254)` | nullable           | Correo general.                                             |
| `phone`                      | `VARCHAR(40)`  | nullable           | Teléfono general.                                           |
| `address_line`               | `TEXT`         | nullable           | Dirección.                                                  |
| `country_id`                 | `UUID`         | REF, nullable      | País administrado por Geography Service.                    |
| `administrative_division_id` | `UUID`         | REF, nullable      | División administrativa administrada por Geography Service. |
| `city_id`                    | `UUID`         | REF, nullable      | Ciudad o municipio administrado por Geography Service.      |
| `postal_code`                | `VARCHAR(20)`  | nullable           | Código postal.                                              |
| `is_active`                  | `BOOLEAN`      | NN, DEFAULT `TRUE` | Versión vigente.                                            |
| `valid_from`                 | `TIMESTAMPTZ`  | NN                 | Inicio de vigencia.                                         |
| `valid_to`                   | `TIMESTAMPTZ`  | nullable           | Fin de vigencia.                                            |
| `confirmed_by_user_id`       | `UUID`         | REF, NN            | Usuario que confirmó.                                       |
| `confirmed_by_company_id`    | `UUID`         | REF, NN            | Empresa desde la que se confirmó.                           |
| `created_at`                 | `TIMESTAMPTZ`  | NN                 | Creación.                                                   |
| `updated_at`                 | `TIMESTAMPTZ`  | NN                 | Modificación.                                               |

### Reglas y restricciones

- Debe existir como máximo una versión activa por `organization_identity_id`.
- Al menos uno de `email`, `phone` o `address_line` debe contener un valor.
- Una versión activa debe tener `valid_to = NULL`; una histórica debe tener `valid_to` informado.
- La geografía debe ser consistente entre país, división administrativa y ciudad.
- Las versiones históricas no se eliminan físicamente.
- `country_id`, `administrative_division_id` y `city_id` son referencias externas a Geography Service y no utilizan llaves foráneas físicas.

## 4.14 OrganizationContactPerson

**Tabla:** `organization_contact_persons`  
**Naturaleza:** global, compartida y con acceso controlado.  
**Servicio propietario:** Party Identity Service.

### Descripción

Representa una persona de contacto asociada con una organización global para funciones comerciales, logísticas, administrativas o de cartera.

Puede vincular opcionalmente una `PersonIdentity` cuando la persona está formalmente identificada.

### Atributos

| Atributo                   | Tipo           | Regla               | Descripción                                   |
| -------------------------- | -------------- | ------------------- | --------------------------------------------- |
| `id`                       | `UUID`         | PK, NN              | Identificador.                                |
| `organization_identity_id` | `UUID`         | FK, NN              | Organización.                                 |
| `person_identity_id`       | `UUID`         | FK, nullable        | Identidad global de la persona cuando exista. |
| `position`                 | `VARCHAR(120)` | nullable            | Cargo o función.                              |
| `email`                    | `VARCHAR(254)` | nullable            | Correo laboral o de contacto.                 |
| `phone`                    | `VARCHAR(40)`  | nullable            | Teléfono.                                     |
| `is_primary`               | `BOOLEAN`      | NN, DEFAULT `FALSE` | Contacto general principal.                   |
| `is_active`                | `BOOLEAN`      | NN, DEFAULT `TRUE`  | Vigencia.                                     |
| `created_at`               | `TIMESTAMPTZ`  | NN                  | Creación.                                     |
| `updated_at`               | `TIMESTAMPTZ`  | NN                  | Modificación.                                 |

### Reglas y restricciones

- Al menos uno de `email`, `phone` o `person_identity_id` debe existir.
- Una organización puede tener varios contactos activos.
- Los contactos históricos utilizados en relaciones u operaciones no se eliminan físicamente.

## 4.15 OrganizationBusinessSector

**Tabla:** `organization_business_sectors`  
**Naturaleza:** global, relacional y versionada.  
**Servicio propietario:** Party Identity Service.

### Descripción

Relaciona una organización con uno o varios sectores económicos gobernados por `GlobalBusinessSector`.

Permite distinguir el sector principal de actividades secundarias y conservar cambios históricos.

### Atributos

| Atributo                    | Tipo          | Regla               | Descripción                                                 |
| --------------------------- | ------------- | ------------------- | ----------------------------------------------------------- |
| `id`                        | `UUID`        | PK, NN              | Identificador.                                              |
| `organization_identity_id`  | `UUID`        | FK, NN              | Organización administrada dentro de Party Identity Service. |
| `global_business_sector_id` | `UUID`        | FK, NN              | Sector económico global asociado a la organización.         |
| `is_primary`                | `BOOLEAN`     | NN, DEFAULT `FALSE` | Sector principal.                                           |
| `is_active`                 | `BOOLEAN`     | NN, DEFAULT `TRUE`  | Vigencia.                                                   |
| `valid_from`                | `TIMESTAMPTZ` | NN                  | Inicio de vigencia.                                         |
| `valid_to`                  | `TIMESTAMPTZ` | nullable            | Fin de vigencia.                                            |
| `created_at`                | `TIMESTAMPTZ` | NN                  | Creación.                                                   |
| `updated_at`                | `TIMESTAMPTZ` | NN                  | Modificación.                                               |

### Reglas y restricciones

- Una organización puede tener varios sectores activos, pero como máximo uno marcado como principal.
- La misma combinación organización-sector no puede repetirse simultáneamente activa.
- Los cambios deben conservar historial de vigencia.

## 4.16 OrganizationLegalRepresentative

**Tabla:** `organization_legal_representatives`  
**Naturaleza:** global, sensible y versionada.  
**Servicio propietario:** Party Identity Service.

### Descripción

Representa la relación histórica entre una organización y la persona que ejerce su representación legal.

El nombre del representante no se almacena directamente en `Company` se obtiene desde `PersonIdentity` a través de esta relación, así se conserva el cambio de representante sin alterar la historia de la empresa.

### Atributos

| Atributo                    | Tipo           | Regla              | Descripción                                                           |
| --------------------------- | -------------- | ------------------ | --------------------------------------------------------------------- |
| `id`                        | `UUID`         | PK, NN             | Identificador.                                                        |
| `organization_identity_id`  | `UUID`         | FK, NN             | Organización representada.                                            |
| `person_identity_id`        | `UUID`         | FK, NN             | Persona representante.                                                |
| `representative_type`       | `VARCHAR(30)`  | NN, CK             | `PRIMARY`, `ALTERNATE` u `OTHER`.                                     |
| `position`                  | `VARCHAR(120)` | nullable           | Denominación del cargo.                                               |
| `is_primary`                | `BOOLEAN`      | NN, DEFAULT `TRUE` | Indica representante principal.                                       |
| `is_active`                 | `BOOLEAN`      | NN, DEFAULT `TRUE` | Vigencia.                                                             |
| `valid_from`                | `TIMESTAMPTZ`  | NN                 | Inicio de vigencia.                                                   |
| `valid_to`                  | `TIMESTAMPTZ`  | nullable           | Fin de vigencia.                                                      |
| `source_document_reference` | `TEXT`         | nullable           | Referencia al documento que soporta la representación cuando aplique. |
| `created_by_user_id`        | `UUID`         | REF, NN            | Usuario que registró la relación.                                     |
| `created_at`                | `TIMESTAMPTZ`  | NN                 | Creación.                                                             |
| `updated_at`                | `TIMESTAMPTZ`  | NN                 | Modificación.                                                         |

### Reglas y restricciones

- Debe existir como máximo un representante principal activo por organización cuando la política legal aplicable así lo requiera.
- Una relación histórica debe cerrar `valid_to` y no eliminarse físicamente.
- La persona y la organización deben estar activas para nuevas asignaciones.

# 5. Commercial Relationship DB — Entidades privadas por empresa

## 5.1 CompanyProduct

**Tabla:** `company_products`

**Naturaleza:** privada por empresa.

**Servicio propietario:** Commercial Relationship Service.

### Descripción

Representa la adopción y configuración privada de un producto global dentro de una empresa.

`GlobalProduct` define qué es el producto de manera global, mientras `CompanyProduct` indica que una empresa decidió incorporarlo a su catálogo y define la configuración general con la que lo administra.

Dos empresas pueden adoptar el mismo `GlobalProduct` y mantener códigos internos, referencias, nombres visibles, precios de referencia, costos de referencia y configuraciones de inventario diferentes.

La entidad no representa una presentación física específica. Las presentaciones que una empresa decide comprar o vender pertenecen a `CompanyProductPresentation`.

Para el MVP, `sale_price` representa el precio simple o predeterminado del producto. Cuando se utilicen listas de precios, los valores específicos pertenecen a `PriceList` y `PriceListItem`.

No almacena stock actual, movimientos, lotes reales ni niveles de reposición por sucursal, ya que estos datos pertenecen a Inventory Service.

### Atributos

| Atributo                      | Tipo            | Regla               | Descripción                                                                                   |
| ----------------------------- | --------------- | ------------------- | --------------------------------------------------------------------------------------------- |
| `id`                          | `UUID`          | PK, NN              | Identificador empresarial.                                                                    |
| `company_id`                  | `UUID`          | REF, NN             | Empresa propietaria.                                                                          |
| `global_product_id`           | `UUID`          | REF, NN             | Producto global adoptado desde Product Catalog Service.                                       |
| `internal_code`               | `VARCHAR(60)`   | NN                  | Código interno principal utilizado por la empresa.                                            |
| `reference_code`              | `VARCHAR(100)`  | nullable            | Referencia adicional del producto; no necesariamente única.                                   |
| `display_name`                | `VARCHAR(200)`  | NN                  | Nombre visible dentro de la empresa.                                                          |
| `short_name`                  | `VARCHAR(160)`  | nullable            | Nombre corto utilizado en interfaces o procesos internos.                                     |
| `sale_price`                  | `NUMERIC(18,2)` | NN, DEFAULT `0`     | Precio simple o predeterminado utilizado cuando no aplica una lista de precios específica.    |
| `currency_code`               | `CHAR(3)`       | NN                  | Moneda ISO 4217 del precio de referencia.                                                     |
| `reference_cost`              | `NUMERIC(18,4)` | NN, DEFAULT `0`     | Costo privado de referencia; no reemplaza el costo histórico calculado por Inventory Service. |
| `inventory_control_enabled`   | `BOOLEAN`       | NN, DEFAULT `TRUE`  | Indica si la empresa controla existencias del producto mediante Inventory Service.            |
| `lot_tracking_enabled`        | `BOOLEAN`       | NN, DEFAULT `FALSE` | Indica si la empresa requiere controlar el producto por lotes.                                |
| `expiration_tracking_enabled` | `BOOLEAN`       | NN, DEFAULT `FALSE` | Indica si los lotes del producto requieren fecha de vencimiento.                              |
| `is_purchasable`              | `BOOLEAN`       | NN, DEFAULT `TRUE`  | Disponible para nuevas operaciones de compra.                                                 |
| `is_sellable`                 | `BOOLEAN`       | NN, DEFAULT `TRUE`  | Disponible para nuevas operaciones de venta.                                                  |
| `status`                      | `VARCHAR(20)`   | NN, CK, DEFAULT `'ACTIVE'` | Estado del producto dentro de la empresa: `ACTIVE` o `INACTIVE`.                       |
| `created_by`                  | `VARCHAR(255)`  | NN                  | `sub` del token de quien crea el registro (Constitución D1); inmutable.                        |
| `updated_by`                  | `VARCHAR(255)`  | NN                  | `sub` del token de quien realizó la última modificación (Constitución D1).                     |
| `version`                     | `INTEGER`       | NN, DEFAULT `1`     | Control de concurrencia.                                                                      |
| `created_at`                  | `TIMESTAMPTZ`   | NN                  | Fecha de creación.                                                                            |
| `updated_at`                  | `TIMESTAMPTZ`   | NN                  | Última modificación.                                                                          |

### Reglas y restricciones

- La combinación `company_id` y `global_product_id` debe ser única en cualquier estado: un producto inactivo se reactiva, no se vuelve a adoptar.
- `internal_code` se guarda sin espacios al inicio ni al final, no puede quedar vacío y es único por empresa sin diferenciar mayúsculas y minúsculas (índice único sobre `company_id` y `lower(internal_code)`), en cualquier estado: inactivar no libera el código; para reutilizarlo se cambia antes el del registro inactivo.
- `status` admite `ACTIVE` e `INACTIVE` (`CHECK`); los cambios de estado se hacen con acciones explícitas de inactivar y reactivar.
- `reference_code` no tiene obligación de ser único.
- `global_product_id` es una referencia externa a Product Catalog Service y no utiliza una llave foránea física.
- Solo un `GlobalProduct` activo puede utilizarse para crear una nueva adopción empresarial.
- `sale_price` y `reference_cost` no pueden ser negativos.
- `lot_tracking_enabled = TRUE` requiere `inventory_control_enabled = TRUE`.
- `expiration_tracking_enabled = TRUE` requiere `lot_tracking_enabled = TRUE`.
- Cuando `inventory_control_enabled = FALSE`, el producto no debe generar nuevos saldos, movimientos, políticas o lotes ordinarios en Inventory Service.
- El stock mínimo y demás niveles de reposición no pertenecen a esta entidad; se configuran por sucursal mediante `InventoryPolicy`.
- Un producto empresarial con `status = INACTIVE` no puede utilizarse en nuevas operaciones ordinarias.
- La desactivación no elimina compras, ventas, precios, inventario o relaciones históricas.

> **Reconciliación (2026-10-04):** sección alineada con `specs/007-commercial-relationship-core`
> (Commercial Relationship Fase A): `status` con `CHECK` en lugar de `is_active` (BR-01) y auditoría
> `created_by`/`updated_by` con el `sub` en lugar de `created_by_user_id` (BR-02). Los nombres de
> restricciones e índices están en el `data-model.md` de esa feature.

### Relaciones

- Pertenece a una empresa mediante `company_id`.
- Referencia un `GlobalProduct` de Product Catalog Service mediante `global_product_id`.
- Puede tener múltiples `CompanyProductPresentation`.
- Puede tener precios específicos mediante `PriceListItem`.
- Puede relacionarse con múltiples proveedores mediante `SupplierProduct`.
- Es referenciado desde Purchase Service, Sales Service e Inventory Service mediante su UUID.
- Puede tener lotes en Inventory Service cuando `lot_tracking_enabled = TRUE`.

## 5.2 CustomerSegment

**Tabla:** `customer_segments`  
**Naturaleza:** catálogo maestro privado por empresa.  
**Servicio propietario:** Commercial Relationship Service.

### Descripción

Representa la segmentación comercial que una empresa utiliza para clasificar sus clientes sin almacenar categorías como texto libre.

Hace referencia a una **clasificación comercial utilizada para agrupar clientes con características o comportamientos similares** de modo que la empresa pueda aplicar análisis, estrategias de venta, precios, promociones o atención diferenciada por ejemplo podrían existir segmentos como `MAYORISTA`, `MINORISTA`, `DISTRIBUIDOR`, `CLIENTE_FRECUENTE`, `CORPORATIVO` o `VIP`.

La segmentación es privada porque dos empresas pueden clasificar al mismo cliente de manera diferente.

### Atributos

| Atributo            | Tipo           | Regla              | Descripción                                |
| ------------------- | -------------- | ------------------ | ------------------------------------------ |
| `id`                | `UUID`         | PK, NN             | Identificador.                             |
| `company_id`        | `UUID`         | REF, NN            | Empresa propietaria.                       |
| `parent_segment_id` | `UUID`         | FK, nullable       | Segmento superior cuando exista jerarquía. |
| `code`              | `VARCHAR(40)`  | NN                 | Código interno.                            |
| `name`              | `VARCHAR(120)` | NN                 | Nombre.                                    |
| `description`       | `TEXT`         | nullable           | Alcance.                                   |
| `is_active`         | `BOOLEAN`      | NN, DEFAULT `TRUE` | Vigencia.                                  |
| `created_at`        | `TIMESTAMPTZ`  | NN                 | Creación.                                  |
| `updated_at`        | `TIMESTAMPTZ`  | NN                 | Modificación.                              |

### Reglas y restricciones

- `code` es único por empresa.
- `parent_segment_id` debe pertenecer a la misma empresa.
- Se deben impedir ciclos jerárquicos.

## 5.3 CompanyCustomer

**Tabla:** `company_customers`  
**Naturaleza:** privada por empresa.  
**Servicio propietario:** Commercial Relationship Service.

### Descripción

Representa la relación privada entre una empresa y una persona u organización que actúa como cliente.

`PersonIdentity` u `OrganizationIdentity` define quién es el cliente, mientras `CompanyCustomer` permite que la empresa lo incorpore a su propia lista, le asigne un código interno y controle si puede utilizarse en ventas nuevas.

Los datos generales de contacto no se duplican en esta entidad.

Cuando el cliente es una persona se consultan desde `PersonContactProfile` y cuando es una organización se consultan desde `OrganizationContactProfile`.

El cliente no necesita tener una cuenta ni una interfaz en SIO.

Esta entidad es administrada exclusivamente por los usuarios autorizados de la empresa.

### Atributos

| Atributo                      | Tipo           | Regla              | Descripción                                                                  |
| ----------------------------- | -------------- | ------------------ | ---------------------------------------------------------------------------- |
| `id`                          | `UUID`         | PK, NN             | Identificador privado.                                                       |
| `company_id`                  | `UUID`         | REF, NN            | Empresa propietaria.                                                         |
| `customer_kind`               | `VARCHAR(20)`  | NN, CK             | `PERSON` u `ORGANIZATION`.                                                   |
| `person_identity_id`          | `UUID`         | REF, nullable      | Identidad global de persona natural administrada por Party Identity Service. |
| `organization_identity_id`    | `UUID`         | REF, nullable      | Identidad global de organización administrada por Party Identity Service.    |
| `internal_code`               | `VARCHAR(60)`  | NN                 | Código interno del cliente.                                                  |
| `display_name`                | `VARCHAR(200)` | NN                 | Nombre visible dentro de la empresa.                                         |
| `preferred_contact_person_id` | `UUID`         | REF, nullable      | Persona de contacto preferida administrada por Party Identity Service.       |
| `status`                      | `VARCHAR(20)`  | NN, CK, DEFAULT `'ACTIVE'` | `ACTIVE` (disponible para ventas nuevas) o `INACTIVE`.               |
| `created_by`                  | `VARCHAR(255)` | NN                 | `sub` del token de quien crea el registro (Constitución D1); inmutable.      |
| `updated_by`                  | `VARCHAR(255)` | NN                 | `sub` del token de quien realizó la última modificación (Constitución D1).   |
| `version`                     | `INTEGER`      | NN, DEFAULT `1`    | Control concurrente.                                                         |
| `created_at`                  | `TIMESTAMPTZ`  | NN                 | Creación.                                                                    |
| `updated_at`                  | `TIMESTAMPTZ`  | NN                 | Modificación.                                                                |

### Reglas y restricciones

- `internal_code` se guarda sin espacios al inicio ni al final, no puede quedar vacío y es único por empresa sin diferenciar mayúsculas y minúsculas (índice único sobre `company_id` y `lower(internal_code)`), en cualquier estado.
- `status` admite `ACTIVE` e `INACTIVE` (`CHECK`); los cambios de estado se hacen con acciones explícitas de inactivar y reactivar.
- Cuando `customer_kind` es `PERSON`, `person_identity_id` es obligatorio y `organization_identity_id` debe ser nulo.
- Cuando `customer_kind` es `ORGANIZATION`, `organization_identity_id` es obligatorio y `person_identity_id` debe ser nulo.
- `preferred_contact_person_id` solo puede informarse para clientes `ORGANIZATION` y debe pertenecer a la misma `OrganizationIdentity`.
- Una empresa solo puede relacionarse una vez con la misma identidad global, en cualquier estado (índices únicos parciales sobre `company_id` y `person_identity_id` u `organization_identity_id`).
- Solo clientes con `status = ACTIVE` pueden utilizarse en ventas nuevas.
- Los datos generales de contacto se consultan en el perfil global activo correspondiente y no se duplican por empresa.
- El saldo de cartera no pertenece a esta entidad y se consulta desde `Finance Service`.

### Relaciones

- Se utiliza desde `Sale` mediante `company_customer_id`.
- Puede tener condiciones de compra mediante `CustomerPaymentCondition` y evaluación crediticia mediante `CustomerCreditProfile`.
- Consulta `PersonContactProfile` o `OrganizationContactProfile` según `customer_kind`.

> **Reconciliación (2026-10-04):** sección alineada con `specs/007-commercial-relationship-core`
> (Commercial Relationship Fase A): `status` con `CHECK` en lugar de `is_active` (BR-01); auditoría
> `created_by`/`updated_by` con el `sub` en lugar de `created_by_user_id` (BR-02); `internal_code`
> único sin diferenciar mayúsculas (BR-04). **Segmentación (BR-03):** `customer_segment_id` no
> forma parte de la Fase A ni del MVP. `CustomerSegment` (§5.2) pertenece a una evolución
> posterior; la Spec que lo introduzca definirá su relación con `CompanyCustomer` y la agregará
> mediante una migración nueva.

## 5.4 CompanySupplier

**Tabla:** `company_suppliers`  
**Naturaleza:** privada por empresa.  
**Servicio propietario:** Commercial Relationship Service.

### Descripción

Representa la relación privada entre una empresa y una organización global seleccionada como proveedor.

`OrganizationIdentity` define quién es legalmente el proveedor, mientras `CompanySupplier` almacena cómo lo identifica la empresa y si está habilitado para compras nuevas.

El correo, teléfono y dirección generales se consultan desde la versión activa de `OrganizationContactProfile`; no se duplican en cada relación `CompanySupplier`.

El proveedor no necesita tener una cuenta ni una interfaz en SIO.

Una compra utiliza `company_supplier_id`, no `organization_identity_id` porque el proveedor debe estar previamente seleccionado y activo para la empresa que compra.

### Atributos

| Atributo                      | Tipo           | Regla           | Descripción                                                            |
| ----------------------------- | -------------- | --------------- | ---------------------------------------------------------------------- |
| `id`                          | `UUID`         | PK, NN          | Identificador privado.                                                 |
| `company_id`                  | `UUID`         | REF, NN         | Empresa propietaria.                                                   |
| `organization_identity_id`    | `UUID`         | REF, NN         | Organización global administrada por Party Identity Service.           |
| `internal_code`               | `VARCHAR(60)`  | NN              | Código interno.                                                        |
| `display_name`                | `VARCHAR(200)` | NN              | Nombre visible en la empresa.                                          |
| `preferred_contact_person_id` | `UUID`         | REF, nullable   | Persona de contacto preferida administrada por Party Identity Service. |
| `status`                      | `VARCHAR(20)`  | NN, CK, DEFAULT `'ACTIVE'` | `ACTIVE`, `INACTIVE` o `BLOCKED`.                           |
| `block_reason`                | `VARCHAR(500)` | nullable        | Motivo del bloqueo: obligatorio con `BLOCKED` y nulo en los demás estados. |
| `created_by`                  | `VARCHAR(255)` | NN              | `sub` del token de quien crea el registro (Constitución D1); inmutable. |
| `updated_by`                  | `VARCHAR(255)` | NN              | `sub` del token de quien realizó la última modificación (Constitución D1). |
| `version`                     | `INTEGER`      | NN, DEFAULT `1` | Control concurrente.                                                   |
| `created_at`                  | `TIMESTAMPTZ`  | NN              | Creación.                                                              |
| `updated_at`                  | `TIMESTAMPTZ`  | NN              | Modificación.                                                          |

### Reglas y restricciones

- Una empresa solo puede seleccionar una vez la misma organización, en cualquier estado.
- `internal_code` se guarda sin espacios al inicio ni al final, no puede quedar vacío y es único por empresa sin diferenciar mayúsculas y minúsculas (índice único sobre `company_id` y `lower(internal_code)`), en cualquier estado.
- `status` admite `ACTIVE`, `INACTIVE` y `BLOCKED` (`CHECK`); los cambios de estado se hacen con acciones explícitas de inactivar, reactivar, bloquear y desbloquear (un proveedor `BLOCKED` se desbloquea; no se reactiva directamente).
- `block_reason` es obligatorio al pasar a `BLOCKED` (texto de 1 a 500 caracteres que no quede vacío tras recortar espacios), se conserva mientras el proveedor esté `BLOCKED` y se borra al desbloquear; en cualquier otro estado es nulo (`CHECK` de consistencia entre `status` y `block_reason`). El historial de bloqueos corresponde a audit-service.
- Solo proveedores `ACTIVE` pueden utilizarse en compras nuevas.
- Los datos generales de contacto se consultan en `OrganizationContactProfile` y no se duplican por empresa.
- El saldo de cartera del proveedor no pertenece a esta entidad; se consulta desde Finance Service.
- `preferred_contact_person_id` cuando exista, debe pertenecer a la misma `OrganizationIdentity` seleccionada como proveedor.

### Relaciones

- Se utiliza desde `Purchase` mediante `company_supplier_id`.
- Puede tener varias condiciones de pago vigentes mediante `SupplierPaymentCondition`.
- Consulta la versión activa de `OrganizationContactProfile`.

> **Reconciliación (2026-10-04):** sección alineada con `specs/007-commercial-relationship-core`
> (Commercial Relationship Fase A): `status` con `CHECK` en lugar de `relationship_status` (BR-01);
> auditoría `created_by`/`updated_by` con el `sub` en lugar de `created_by_user_id` (BR-02);
> `internal_code` único sin diferenciar mayúsculas (BR-04); `block_reason` obligatorio con
> `BLOCKED` (BR-05).

## 5.5 SupplierCommercialCondition

**Tabla:** `supplier_commercial_conditions`  
**Naturaleza:** privada, comercial y versionada por empresa.  
**Servicio propietario:** Commercial Relationship Service.

### Descripción

Conserva condiciones comerciales generales negociadas entre una empresa y uno de sus proveedores como mínimos de pedido, descuentos y observaciones contractuales. Se separa de `CompanySupplier` para conservar historial.

Las condiciones de pago se administran en `SupplierPaymentCondition` y las condiciones específicas de producto en `SupplierProduct`.

### Atributos

| Atributo                | Tipo            | Regla              | Descripción                          |
| ----------------------- | --------------- | ------------------ | ------------------------------------ |
| `id`                    | `UUID`          | PK, NN             | Identificador.                       |
| `company_id`            | `UUID`          | REF, NN            | Empresa propietaria.                 |
| `company_supplier_id`   | `UUID`          | FK, NN             | Proveedor privado.                   |
| `currency_code`         | `CHAR(3)`       | NN                 | Moneda principal de las condiciones. |
| `minimum_order_value`   | `NUMERIC(18,2)` | nullable           | Valor mínimo general de pedido.      |
| `discount_percentage`   | `NUMERIC(7,4)`  | nullable           | Descuento general pactado.           |
| `commercial_conditions` | `TEXT`          | nullable           | Condiciones adicionales.             |
| `is_active`             | `BOOLEAN`       | NN, DEFAULT `TRUE` | Versión vigente.                     |
| `valid_from`            | `TIMESTAMPTZ`   | NN                 | Inicio de vigencia.                  |
| `valid_to`              | `TIMESTAMPTZ`   | nullable           | Fin de vigencia.                     |
| `created_by_user_id`    | `UUID`          | REF, NN            | Usuario creador.                     |
| `created_at`            | `TIMESTAMPTZ`   | NN                 | Creación.                            |
| `updated_at`            | `TIMESTAMPTZ`   | NN                 | Modificación.                        |

### Reglas y restricciones

- Debe existir como máximo una condición comercial general activa por `company_supplier_id` y moneda.
- Una versión histórica debe conservarse y no se sobrescribe.
- Valores monetarios y porcentajes no pueden ser negativos.

## 5.6 SupplierPaymentCondition

**Tabla:** `supplier_payment_conditions`  
**Naturaleza:** privada, comercial y versionada por empresa.  
**Servicio propietario:** Commercial Relationship Service.

### Descripción

Representa las formas de financiación o exigibilidad que un proveedor ofrece a una empresa por ejemplo contado, crédito a 30 días o financiación a 60 días.

Un mismo proveedor puede ofrecer más de una condición activa.

La existencia de una condición `CREDIT` no significa que exista deuda, la deuda nace cuando una compra confirmada genera una `AccountPayable` en `Finance Service`.

### Atributos

| Atributo                    | Tipo            | Regla               | Descripción                                                                  |
| --------------------------- | --------------- | ------------------- | ---------------------------------------------------------------------------- |
| `id`                        | `UUID`          | PK, NN              | Identificador.                                                               |
| `company_id`                | `UUID`          | REF, NN             | Empresa propietaria.                                                         |
| `company_supplier_id`       | `UUID`          | FK, NN              | Proveedor privado.                                                           |
| `payment_condition_type_id` | `UUID`          | REF, NN             | Tipo global de condición de pago administrado por Payment Reference Service. |
| `currency_code`             | `CHAR(3)`       | NN                  | Moneda.                                                                      |
| `payment_terms_days`        | `INTEGER`       | NN, DEFAULT `0`     | Días concedidos para el pago.                                                |
| `credit_limit`              | `NUMERIC(18,2)` | nullable            | Cupo de crédito concedido por el proveedor.                                  |
| `interest_rate_percentage`  | `NUMERIC(7,4)`  | nullable            | Tasa asociada a financiación cuando aplique.                                 |
| `cash_discount_percentage`  | `NUMERIC(7,4)`  | nullable            | Descuento por pago de contado cuando aplique.                                |
| `is_default`                | `BOOLEAN`       | NN, DEFAULT `FALSE` | Condición sugerida por defecto.                                              |
| `status` | `VARCHAR(20)` | NN, CK, DEFAULT `'ACTIVE'` | Estado de la condición: `ACTIVE` o `INACTIVE`. |
| `valid_from`                | `TIMESTAMPTZ`   | NN                  | Inicio de vigencia.                                                          |
| `valid_to`                  | `TIMESTAMPTZ`   | nullable            | Fin de vigencia.                                                             |
| `created_by` | `VARCHAR(255)` | NN | `sub` del token de quien crea el registro (Constitución D1); inmutable. |
| `updated_by` | `VARCHAR(255)` | NN | `sub` del token de quien realizó la última modificación (Constitución D1). |
| `version` | `INTEGER` | NN, DEFAULT `1` | Control de concurrencia. |
| `created_at`                | `TIMESTAMPTZ`   | NN                  | Creación.                                                                    |
| `updated_at`                | `TIMESTAMPTZ`   | NN                  | Modificación.                                                                |

### Reglas y restricciones

- `status` admite `ACTIVE` e `INACTIVE` (`CHECK`); los cambios de estado se hacen con acciones explícitas de inactivar y reactivar, sin eliminar el registro.
- Puede existir más de una condición activa por proveedor, pero como máximo una condición predeterminada por moneda.
- `CASH` debe usar `payment_terms_days = 0`.
- `CREDIT` y `FINANCING` deben utilizar un plazo mayor que cero.
- Cupos, tasas y descuentos no pueden ser negativos.
- Las versiones utilizadas en compras históricas no se eliminan físicamente.
- `payment_condition_type_id` es una referencia externa a Payment Reference Service y no utiliza una llave foránea física.

> **Reconciliación (2026-10-05):** sección alineada con `specs/010-commercial-relationship-commercial-product`
> (Commercial Relationship Fase B): `status` con `CHECK` en lugar de `is_active` (BR-06); auditoría
> `created_by`/`updated_by` con el `sub` en lugar de `created_by_user_id` y `version` para el control de
> concurrencia (BR-07). Los nombres de restricciones e índices están en el `data-model.md` de esa feature.

## 5.7 SupplierProduct

**Tabla:** `supplier_products`  
**Naturaleza:** privada y comercial por empresa.  
**Servicio propietario:** Commercial Relationship Service.

### Descripción

Representa la relación entre un proveedor seleccionado por una empresa y un producto empresarial que dicho proveedor puede suministrar.

Es la base para comparar a proveedores, almacenar costos negociados, lead time esperado, cantidades mínimas de compra y preferencias de abastecimiento.

El lead time esperado es una condición de planificación y no reemplaza el lead time real observado en las compras.

### Atributos

| Atributo                            | Tipo            | Regla               | Descripción                                                                       |
| ----------------------------------- | --------------- | ------------------- | --------------------------------------------------------------------------------- |
| `id`                                | `UUID`          | PK, NN              | Identificador.                                                                    |
| `company_id`                        | `UUID`          | REF, NN             | Empresa propietaria.                                                              |
| `company_supplier_id`               | `UUID`          | FK, NN              | Proveedor privado.                                                                |
| `company_product_id`                | `UUID`          | FK, NN              | Producto empresarial.                                                             |
| `company_product_presentation_id`   | `UUID`          | FK, nullable        | Presentación empresarial específica suministrada por el proveedor cuando aplique. |
| `supplier_product_code`             | `VARCHAR(100)`  | nullable            | Código utilizado por el proveedor.                                                |
| `purchase_unit_id`                  | `UUID`          | REF, NN             | Unidad global acordada para compra, administrada por Product Catalog Service.     |
| `minimum_order_quantity`            | `NUMERIC(18,4)` | NN, DEFAULT `0`     | Cantidad mínima de pedido.                                                        |
| `pack_quantity`                     | `NUMERIC(18,4)` | NN, DEFAULT `1`     | Múltiplo o empaque habitual.                                                      |
| `negotiated_unit_cost`              | `NUMERIC(18,4)` | nullable            | Costo unitario negociado de referencia.                                           |
| `currency_code`                     | `CHAR(3)`       | NN                  | Moneda del costo negociado.                                                       |
| `expected_supplier_lead_time_hours` | `NUMERIC(12,2)` | nullable            | Lead time comprometido o esperado del proveedor.                                  |
| `priority`                          | `SMALLINT`      | nullable            | Prioridad manual para abastecimiento.                                             |
| `is_preferred`                      | `BOOLEAN`       | NN, DEFAULT `FALSE` | Proveedor preferido para el producto.                                             |
| `status` | `VARCHAR(20)` | NN, CK, DEFAULT `'ACTIVE'` | Estado de la relación: `ACTIVE` o `INACTIVE`. |
| `created_by` | `VARCHAR(255)` | NN | `sub` del token de quien crea el registro (Constitución D1); inmutable. |
| `updated_by` | `VARCHAR(255)` | NN | `sub` del token de quien realizó la última modificación (Constitución D1). |
| `version`                           | `INTEGER`       | NN, DEFAULT `1`     | Control concurrente.                                                              |
| `created_at`                        | `TIMESTAMPTZ`   | NN                  | Creación.                                                                         |
| `updated_at`                        | `TIMESTAMPTZ`   | NN                  | Modificación.                                                                     |

### Reglas y restricciones

- Entre los registros `ACTIVE`, la combinación `company_supplier_id`, `company_product_id` y `company_product_presentation_id` es única; la ausencia de presentación cuenta como un valor. Los registros `INACTIVE` no cuentan y reactivar revalida la unicidad.
- `status` admite `ACTIVE` e `INACTIVE` (`CHECK`); los cambios de estado se hacen con acciones explícitas de inactivar y reactivar, sin eliminar el registro.
- Costos, cantidades y lead times esperados no pueden ser negativos.
- `pack_quantity` debe ser mayor que cero.
- Solo proveedores y productos activos pueden utilizarse para nuevas compras.
- Puede existir un único proveedor marcado como preferido por producto y empresa cuando la política de negocio así lo exija.
- Cuando exista `company_product_presentation_id`, la presentación debe pertenecer al mismo `company_product_id`.
- Si `company_product_presentation_id` es nulo, la relación con el proveedor aplica al producto empresarial de forma general.

> **Reconciliación (2026-10-05):** sección alineada con `specs/010-commercial-relationship-commercial-product`
> (Commercial Relationship Fase B): `status` con `CHECK` en lugar de `is_active` (BR-06); auditoría
> `created_by`/`updated_by` con el `sub` en lugar de `created_by_user_id` (BR-07); unicidad por
> proveedor, producto y presentación entre los registros `ACTIVE` (BR-08). Los nombres de restricciones e
> índices están en el `data-model.md` de esa feature.

### Relaciones

- Pertenece a `CompanySupplier` y `CompanyProduct`.
- Puede relacionarse con una `CompanyProductPresentation` específica.
- Puede ser referenciado desde `PurchaseDetail` para conservar el origen comercial de la línea.

## 5.8 ProductPricingPolicy

**Tabla:** `product_pricing_policies`  
**Naturaleza:** privada, configurable, histórica y versionada por empresa.  
**Servicio propietario:** Commercial Relationship Service.
**Alcance:** POST-MVP. No requerida para la operación de listas de precios del MVP.

### Descripción

Esta entidad no representa una lista de precios y no participa en el mecanismo básico de precios del MVP.

Durante el MVP, los precios se administran mediante `CompanyProduct.sale_price` como precio simple de referencia y mediante `PriceList` y `PriceListItem` cuando se requiera una lista de precios.

`ProductPricingPolicy` queda reservada para una etapa posterior en la que SIO implemente reglas de margen, control de rentabilidad, alertas comerciales o autorizaciones asociadas al precio.

Representa la política comercial de márgenes que una empresa define para un producto empresarial.

`CompanyProduct` conserva la configuración comercial básica del producto, como su código interno, nombre visible y precio de venta de referencia, mientras `ProductPricingPolicy` establece las reglas utilizadas por SIO para determinar si el margen generado por una venta es comercialmente aceptable.

La política permite definir un margen mínimo, un margen objetivo y un margen máximo para cada producto empresarial.

El margen mínimo representa el límite comercial inferior que normalmente debe respetarse al vender el producto.

El margen objetivo representa la rentabilidad que la empresa espera obtener normalmente.

El margen máximo funciona inicialmente como una referencia comercial superior y puede utilizarse para análisis, recomendaciones de precio y estrategias comerciales, pero no bloquea por sí mismo una venta.

SIO utiliza como referencia el margen bruto porcentual calculado sobre la venta neta antes de impuestos:

```text
gross_margin_percentage =
((net_sale_amount - cost_amount) / net_sale_amount) * 100
```

Donde:

- `net_sale_amount` corresponde al valor de venta después de descuentos y antes de impuestos.
- `cost_amount` corresponde al costo histórico realmente aplicado al inventario vendido.
- El impuesto no forma parte del cálculo del margen comercial.
- El costo definitivo utilizado para evaluar y registrar el margen debe provenir del método de valoración aplicado por Inventory Service.
- `CompanyProduct.reference_cost` puede utilizarse como referencia previa durante una cotización o borrador, pero no representa necesariamente el costo histórico definitivo de una venta confirmada.

La política también determina qué debe hacer SIO cuando una venta genera un margen inferior al mínimo permitido.

Inicialmente las acciones permitidas son:

- `BLOCK`: impedir la confirmación de la venta.
- `REQUIRE_APPROVAL`: solicitar autorización antes de permitir la operación.
- `ALLOW_WITH_ALERT`: permitir la operación generando una alerta.

Cuando esta capacidad está habilitada, Intelligence Service puede utilizar el costo estimado o definitivo, el margen objetivo, el comportamiento histórico, la demanda y otros datos disponibles para recomendar un precio.

Las políticas son históricamente versionadas.

Cuando cambia cualquier condición que pueda modificar la decisión comercial sobre una venta, la versión vigente no se sobrescribe.

SIO cierra la vigencia de la política actual y crea una nueva fila con la nueva configuración.

Esto permite conocer exactamente qué política se encontraba vigente cuando una venta fue evaluada y analizar posteriormente el efecto de los cambios comerciales sobre ventas, precios, descuentos, márgenes y rentabilidad.

### Atributos

| Atributo                    | Tipo           | Regla              | Descripción                                                                          |
| --------------------------- | -------------- | ------------------ | ------------------------------------------------------------------------------------ |
| `id`                        | `UUID`         | PK, NN             | Identificador único de esta versión histórica de la política.                        |
| `company_id`                | `UUID`         | REF, NN            | Empresa propietaria de la política.                                                  |
| `company_product_id`        | `UUID`         | FK, NN             | Producto empresarial al que aplica la política.                                      |
| `minimum_margin_percentage` | `NUMERIC(7,4)` | NN                 | Margen bruto porcentual mínimo permitido normalmente para el producto.               |
| `target_margin_percentage`  | `NUMERIC(7,4)` | NN                 | Margen bruto porcentual que la empresa espera obtener normalmente.                   |
| `maximum_margin_percentage` | `NUMERIC(7,4)` | NN                 | Margen bruto porcentual máximo utilizado como referencia comercial.                  |
| `below_minimum_action`      | `VARCHAR(30)`  | NN, CK             | Acción que debe ejecutar SIO cuando el margen calculado queda por debajo del mínimo. |
| `is_active`                 | `BOOLEAN`      | NN, DEFAULT `TRUE` | Indica si esta es actualmente la versión vigente de la política.                     |
| `valid_from`                | `TIMESTAMPTZ`  | NN                 | Momento desde el cual esta versión entra en vigencia.                                |
| `valid_to`                  | `TIMESTAMPTZ`  | nullable           | Momento hasta el cual esta versión fue válida; es nulo mientras permanezca vigente.  |
| `created_by_user_id`        | `UUID`         | REF, NN            | Usuario que creó esta versión de la política.                                        |
| `version`                   | `INTEGER`      | NN, DEFAULT `1`    | Control de concurrencia optimista del registro.                                      |
| `created_at`                | `TIMESTAMPTZ`  | NN                 | Fecha y hora de creación de esta versión.                                            |
| `updated_at`                | `TIMESTAMPTZ`  | NN                 | Última modificación técnica permitida sobre el registro.                             |

### Valores permitidos de `below_minimum_action`

Inicialmente se permiten los siguientes valores:

| Código             | Descripción                                                                      |
| ------------------ | -------------------------------------------------------------------------------- |
| `BLOCK`            | Impide confirmar una venta cuyo margen esté por debajo del mínimo configurado.   |
| `REQUIRE_APPROVAL` | Requiere autorización de un usuario con permisos suficientes antes de continuar. |
| `ALLOW_WITH_ALERT` | Permite continuar con la operación, pero genera una alerta comercial.            |

Estos valores representan comportamientos internos del dominio y no son catálogos administrables libremente por cada empresa.

### Reglas de margen

Debe cumplirse siempre:

```text
minimum_margin_percentage
    <= target_margin_percentage
    <= maximum_margin_percentage
```

Los porcentajes no pueden ser negativos.

Inicialmente los márgenes se expresan como porcentajes entre `0` y `100`.

El margen mínimo determina el límite sobre el cual se evalúa `below_minimum_action`.

El margen objetivo no bloquea una venta.

El margen máximo tampoco bloquea una venta y se utiliza inicialmente como referencia para análisis y recomendaciones comerciales.

La fórmula funcional utilizada es:

```text
gross_margin_percentage =
((net_sale_amount - cost_amount) / net_sale_amount) * 100
```

Si `net_sale_amount` es igual a cero, la venta no puede evaluarse mediante esta fórmula y debe ser rechazada o tratada mediante una regla comercial específica antes de su confirmación.

### Versionado histórico

Los siguientes cambios se consideran modificaciones funcionales de la política:

- `minimum_margin_percentage`
- `target_margin_percentage`
- `maximum_margin_percentage`
- `below_minimum_action`
- `ai_price_recommendation_enabled`

Cuando cambia cualquiera de estos valores no debe modificarse directamente la fila vigente.

SIO debe:

1. localizar la política actualmente vigente.
2. validar la versión utilizada para control de concurrencia.
3. cerrar la vigencia de la política actual.
4. establecer `is_active = FALSE`.
5. establecer `valid_to` con el momento efectivo del cambio.
6. crear una nueva fila con la nueva configuración.
7. establecer `valid_from` con el mismo momento efectivo.
8. establecer `valid_to = NULL`.
9. establecer `is_active = TRUE`.
10. realizar todas las operaciones dentro de una misma transacción local.

El cierre de la política anterior y la creación de la nueva deben utilizar exactamente el mismo instante lógico de cambio para evitar espacios temporales entre ambas versiones.

### Diferencia entre vigencia y `version`

`valid_from` y `valid_to` representan el versionado funcional e histórico de la política.

Permiten conocer durante qué período fue válida cada configuración comercial.

### Evaluación durante una venta

Mientras una venta se encuentre en `DRAFT` SIO puede utilizar costos de referencia o estimados para advertir anticipadamente sobre posibles incumplimientos de margen.

Antes de confirmar definitivamente la venta debe utilizarse el costo que corresponda según el método de valoración configurado para la empresa.

Conceptualmente:

```text
SaleDetail
    │
    ├── precio
    ├── descuento
    └── cantidad
          │
          ▼
Calcular venta neta antes de impuestos
          │
          ▼
Obtener costo aplicable
desde Inventory Service
          │
          ▼
Calcular gross_margin_percentage
          │
          ▼
Consultar ProductPricingPolicy vigente
          │
          ▼
Comparar con minimum_margin_percentage
```

Si:

```text
gross_margin_percentage
>= minimum_margin_percentage
```

la venta puede continuar normalmente según las demás reglas de negocio.

Si:

```text
gross_margin_percentage
< minimum_margin_percentage
```

se ejecuta el comportamiento definido en `below_minimum_action`.

### Comportamiento `BLOCK`

Cuando:

```text
below_minimum_action = BLOCK
```

la venta no puede confirmarse mientras el margen continúe por debajo del mínimo.

```text
Margen real
     │
     ▼
Menor al mínimo
     │
     ▼
   BLOCK
     │
     ▼
Confirmación rechazada
```

La operación puede continuar únicamente después de modificar las condiciones comerciales de la venta de manera que vuelva a cumplir la política.

### Comportamiento `REQUIRE_APPROVAL`

Cuando:

```text
below_minimum_action = REQUIRE_APPROVAL
```

SIO debe generar una solicitud de autorización.

```text
Margen real < margen mínimo
              │
              ▼
      REQUIRE_APPROVAL
              │
              ▼
       ApprovalRequest
              │
        ┌─────┴─────┐
        ▼           ▼
    APPROVED      REJECTED
        │           │
        ▼           ▼
     continúa     no continúa
```

La política únicamente determina que se requiere una autorización.

La administración de la solicitud, los usuarios autorizadores, niveles de aprobación, decisión, motivo y trazabilidad pertenece al servicio responsable de workflows y aprobaciones.

Una autorización debe quedar relacionada con la operación concreta que originó la excepción.

### Comportamiento `ALLOW_WITH_ALERT`

Cuando:

```text
below_minimum_action = ALLOW_WITH_ALERT
```

la operación puede continuar, pero SIO debe generar una alerta.

```text
Margen real < margen mínimo
              │
              ▼
      ALLOW_WITH_ALERT
              │
       ┌──────┴──────┐
       ▼             ▼
Generar alerta   Permitir operación
```

La alerta debe identificar como mínimo:

- empresa;
- venta;
- producto;
- margen calculado;
- margen mínimo configurado;
- usuario que realizó la operación;
- momento de la operación.

La administración de la alerta pertenece al servicio responsable de alertas y no a Commercial Relationship Service.

### Relación con descuentos

Los descuentos aplicados sobre una venta afectan el valor neto utilizado para calcular el margen.

Por ejemplo:

```text
Precio unitario = 100.000
Descuento       = 10.000

Venta neta antes de impuestos = 90.000
Costo           = 70.000
```

El margen debe calcularse utilizando:

```text
(90.000 - 70.000) / 90.000
```

y no sobre el precio original de `100.000`.

Esto permite que SIO detecte descuentos que reduzcan excesivamente la rentabilidad.

### Relación con el costo

La política no almacena el costo del producto.

`CompanyProduct.reference_cost` representa únicamente un costo privado de referencia.

El costo histórico definitivo de una venta debe provenir del método de valoración aplicado por `Inventory Service`.

Por ejemplo:

```text
CompanyProduct.reference_cost
= 70.000
```

podría ser diferente del costo real obtenido mediante FIFO:

```text
FIFO cost
= 73.500
```

La evaluación definitiva del margen debe utilizar:

```text
73.500
```

y no:

```text
70.000
```

### Relación con FIFO y promedio ponderado

Cuando la empresa utilice `FIFO`, Inventory Service determina qué capas de inventario fueron consumidas por la venta y calcula el costo correspondiente.

Cuando la empresa utilice `WEIGHTED_AVERAGE`, Inventory Service utiliza el costo promedio vigente según las reglas del método.

`ProductPricingPolicy` no conoce ni implementa estos algoritmos.

Únicamente recibe o utiliza el costo resultante para evaluar el margen.

Conceptualmente:

```text
ProductPricingPolicy
        │
        │ necesita costo
        ▼
Inventory Service
        │
        ├── FIFO
        │
        └── WEIGHTED_AVERAGE
        │
        ▼
Costo real aplicable
        │
        ▼
Evaluación de margen
```

### Trazabilidad en `SaleDetail`

Cuando una venta se confirma, debe conservarse la información necesaria para conocer exactamente cómo fue evaluado el margen.

`SaleDetail` debe incorporar como mínimo:

```text
pricing_policy_id
unit_cost_snapshot
cost_total
gross_margin_amount
gross_margin_percentage
```

También se recomienda conservar:

```text
minimum_margin_snapshot
target_margin_snapshot
maximum_margin_snapshot
```

De esta manera cada línea de venta conserva:

```text
Qué precio se utilizó
Qué descuento se aplicó
Qué costo se utilizó
Qué margen se obtuvo
Qué política se utilizó
Qué límites de margen estaban vigentes
```

Ejemplo:

```text
SaleDetail

unit_price                  = 100.000
unit_cost_snapshot          = 70.000

gross_margin_percentage     = 30 %

pricing_policy_id           = UUID-POLICY-001

minimum_margin_snapshot     = 15 %
target_margin_snapshot      = 25 %
maximum_margin_snapshot     = 40 %
```

Si posteriormente la política cambia a:

```text
minimum = 20 %
target  = 30 %
maximum = 45 %
```

la venta histórica continúa reflejando correctamente:

```text
minimum_margin_snapshot = 15 %
```

porque ese era el límite vigente cuando se realizó.

### Política histórica y ventas anteriores

Una venta nunca debe reinterpretarse utilizando la política vigente actualmente.

Por ejemplo:

```text
Venta realizada:
2026-02-10

Margen obtenido:
12 %

Política vigente:
minimum = 10 %
```

La venta cumplía la política.

Posteriormente:

```text
2026-08-01

Nueva política:
minimum = 15 %
```

La venta histórica de febrero sigue considerándose válida respecto a la política bajo la cual fue confirmada.

No debe realizarse:

```text
Venta antigua
12 % margen

comparada con

política actual
15 %
```

para determinar retrospectivamente si la operación fue válida.

### Auditoría

Los siguientes eventos relacionados con políticas de precios deben generar evidencia de auditoría:

- creación de una política.
- cierre de una política vigente.
- creación de una nueva versión.
- cambio de márgenes.
- cambio de `below_minimum_action`.
- venta bloqueada por margen.
- autorización de una venta por debajo del margen.
- rechazo de una autorización.
- venta permitida con alerta.

`AuditEvent` registra la evidencia histórica de estas acciones pero no sustituye el versionado funcional de `ProductPricingPolicy`.

### Eliminación

Las políticas no deben eliminarse físicamente cuando hayan tenido vigencia o hayan sido utilizadas en operaciones.

Una política vigente que deba dejar de utilizarse debe cerrarse mediante:

```text
is_active = FALSE
valid_to = momento_de_cierre
```

El historial debe conservarse para auditoría, reporting y análisis.

### Relaciones

- Pertenece a una empresa mediante `company_id`.
- Pertenece a un único `CompanyProduct`.
- Un `CompanyProduct` puede tener múltiples versiones históricas de `ProductPricingPolicy`.
- Un `CompanyProduct` puede tener como máximo una política activa.
- `SaleDetail` conserva el `pricing_policy_id` utilizado durante la evaluación de una venta confirmada.
- `SaleDetail` conserva snapshots de costo y margen para proteger la interpretación histórica.
- Inventory Service suministra el costo definitivo utilizado en el cálculo del margen.
- Workflow Service administra las autorizaciones generadas por `REQUIRE_APPROVAL`.
- El servicio responsable de alertas administra los eventos originados por `ALLOW_WITH_ALERT`.
- Intelligence Service puede utilizar la política para generar recomendaciones de precio.
- Audit Service conserva evidencia de las acciones relevantes realizadas sobre la política.
- Reporting Service puede utilizar las versiones históricas para analizar el efecto de cambios de margen sobre ventas y rentabilidad.

## 5.9 CustomerCreditProfile

**Tabla:** `customer_credit_profiles`  
**Naturaleza:** privada, sensible y versionada por empresa.  
**Servicio propietario:** Commercial Relationship Service.

### Descripción

Representa la evaluación crediticia y las condiciones de crédito que una empresa asigna a uno de sus clientes.

Se separa de `CompanyCustomer` porque el riesgo puede cambiar con el tiempo y requiere historial propio.

### Atributos

| Atributo                     | Tipo            | Regla              | Descripción                          |
| ---------------------------- | --------------- | ------------------ | ------------------------------------ |
| `id`                         | `UUID`          | PK, NN             | Identificador.                       |
| `company_id`                 | `UUID`          | REF, NN            | Empresa propietaria.                 |
| `company_customer_id`        | `UUID`          | FK, NN             | Cliente privado.                     |
| `risk_level`                 | `VARCHAR(20)`   | NN, CK             | `LOW`, `MEDIUM`, `HIGH` o `BLOCKED`. |
| `credit_limit`               | `NUMERIC(18,2)` | nullable           | Límite autorizado.                   |
| `maximum_payment_terms_days` | `INTEGER`       | nullable           | Plazo máximo de crédito autorizado.  |
| `assessment_reason`          | `TEXT`          | nullable           | Justificación de la evaluación.      |
| `is_active`                  | `BOOLEAN`       | NN, DEFAULT `TRUE` | Versión vigente.                     |
| `valid_from`                 | `TIMESTAMPTZ`   | NN                 | Inicio de vigencia.                  |
| `valid_to`                   | `TIMESTAMPTZ`   | nullable           | Fin de vigencia.                     |
| `assessed_by_user_id`        | `UUID`          | REF, NN            | Usuario responsable.                 |
| `created_at`                 | `TIMESTAMPTZ`   | NN                 | Creación.                            |
| `updated_at`                 | `TIMESTAMPTZ`   | NN                 | Modificación.                        |

### Reglas y restricciones

- Debe existir como máximo un perfil activo por `company_customer_id`.
- Los perfiles históricos no se eliminan físicamente.
- Los límites y plazos no pueden ser negativos.
- Las métricas de frecuencia, ticket promedio y rentabilidad no se almacenan aquí; pertenecen a Reporting Service. Las condiciones concretas de compra se registran en `CustomerPaymentCondition`.

## 5.10 CustomerPaymentCondition

**Tabla:** `customer_payment_conditions`  
**Naturaleza:** privada, comercial y versionada por empresa.  
**Servicio propietario:** Commercial Relationship Service.

### Descripción

Define las condiciones bajo las cuales un cliente puede comprar a una empresa: contado, crédito o financiación vinculada a la venta.

La condición comercial es diferente del medio con el que posteriormente se recibe el dinero. La deuda resultante de una venta pertenece a `AccountReceivable` en Finance Service.

### Atributos

| Atributo                    | Tipo           | Regla               | Descripción                                 |
| --------------------------- | -------------- | ------------------- | ------------------------------------------- |
| `id`                        | `UUID`         | PK, NN              | Identificador.                              |
| `company_id`                | `UUID`         | REF, NN             | Empresa propietaria.                        |
| `company_customer_id`       | `UUID`         | FK, NN              | Cliente privado.                            |
| `payment_condition_type_id` | `UUID`         | FK, NN              | Tipo global `CASH`, `CREDIT` o `FINANCING`. |
| `payment_terms_days`        | `INTEGER`      | NN, DEFAULT `0`     | Plazo aplicable.                            |
| `interest_rate_percentage`  | `NUMERIC(7,4)` | nullable            | Tasa de financiación cuando aplique.        |
| `cash_discount_percentage`  | `NUMERIC(7,4)` | nullable            | Descuento por contado cuando aplique.       |
| `is_default`                | `BOOLEAN`      | NN, DEFAULT `FALSE` | Condición sugerida.                         |
| `is_active`                 | `BOOLEAN`      | NN, DEFAULT `TRUE`  | Vigencia.                                   |
| `valid_from`                | `TIMESTAMPTZ`  | NN                  | Inicio de vigencia.                         |
| `valid_to`                  | `TIMESTAMPTZ`  | nullable            | Fin de vigencia.                            |
| `created_by_user_id`        | `UUID`         | REF, NN             | Usuario creador.                            |
| `created_at`                | `TIMESTAMPTZ`  | NN                  | Creación.                                   |
| `updated_at`                | `TIMESTAMPTZ`  | NN                  | Modificación.                               |

### Reglas y restricciones

- Puede existir más de una condición activa por cliente, pero como máximo una predeterminada.
- `CASH` debe utilizar `payment_terms_days = 0`.
- `CREDIT` y `FINANCING` requieren un `CustomerCreditProfile` activo que no esté `BLOCKED`.
- El plazo concedido no puede superar `CustomerCreditProfile.maximum_payment_terms_days` cuando dicho límite exista.
- Tasas y descuentos no pueden ser negativos.

## 5.11 SupplierEvaluation

**Tabla:** `supplier_evaluations`  
**Naturaleza:** privada, histórica y evaluativa por empresa.  
**Servicio propietario:** Commercial Relationship Service.

### Descripción

Hace referencia a una evaluación explícita y humana que una empresa realiza sobre uno de sus proveedores.

Sirve para registrar una calificación trazable basada en la experiencia real de la empresa con ese proveedor por ejemplo después de una compra o de una entrega.

Complementa las métricas automáticas de cumplimiento y lead time con una calificación humana trazable.

La calificación histórica agregada se publica desde Reporting Service y no se sobrescribe directamente en `CompanySupplier`.

### Atributos

| Atributo               | Tipo           | Regla         | Descripción                                                                     |
| ---------------------- | -------------- | ------------- | ------------------------------------------------------------------------------- |
| `id`                   | `UUID`         | PK, NN        | Identificador.                                                                  |
| `company_id`           | `UUID`         | REF, NN       | Empresa propietaria.                                                            |
| `company_supplier_id`  | `UUID`         | FK, NN        | Proveedor evaluado.                                                             |
| `purchase_id`          | `UUID`         | REF, nullable | Compra relacionada cuando la evaluación corresponde a una operación específica. |
| `rating`               | `NUMERIC(4,2)` | NN, CK        | Calificación numérica.                                                          |
| `comments`             | `TEXT`         | nullable      | Observaciones.                                                                  |
| `evaluated_by_user_id` | `UUID`         | REF, NN       | Usuario evaluador.                                                              |
| `evaluated_at`         | `TIMESTAMPTZ`  | NN            | Momento de evaluación.                                                          |
| `created_at`           | `TIMESTAMPTZ`  | NN            | Persistencia.                                                                   |

### Reglas y restricciones

- La escala inicial de `rating` es de `0.00` a `5.00`.
- Las evaluaciones históricas no se editan para recalcular el pasado; una corrección se registra mediante una nueva evaluación controlada.
- `SupplierPerformanceMetric.average_rating` se deriva de estas evaluaciones según el periodo definido.

## 5.12 CompanyProductPresentation

**Tabla:** `company_product_presentations`

**Naturaleza:** privada por empresa.

**Servicio propietario:** Commercial Relationship Service.

### Descripción

Representa la adopción empresarial de una presentación global de un producto.

`GlobalProductPresentation` define cómo existe físicamente una presentación, mientras `CompanyProductPresentation` define cómo una empresa utiliza esa presentación para comprarla, venderla o identificarla internamente.

Permite que dos empresas adopten el mismo producto y la misma presentación utilizando códigos internos o SKU diferentes.

### Atributos

| Atributo                         | Tipo           | Regla               | Descripción                                   |
| -------------------------------- | -------------- | ------------------- | --------------------------------------------- |
| `id`                             | `UUID`         | PK, NN              | Identificador empresarial.                    |
| `company_id`                     | `UUID`         | REF, NN             | Empresa propietaria.                          |
| `company_product_id`             | `UUID`         | FK, NN              | Producto empresarial.                         |
| `global_product_presentation_id` | `UUID`         | REF, NN             | Presentación global adoptada.                 |
| `internal_code`                  | `VARCHAR(80)`  | nullable            | Código interno específico de la presentación. |
| `sku`                            | `VARCHAR(80)`  | nullable            | SKU privado de la presentación.               |
| `reference_code`                 | `VARCHAR(100)` | nullable            | Referencia empresarial adicional.             |
| `is_purchasable`                 | `BOOLEAN`      | NN, DEFAULT `TRUE`  | Indica si puede utilizarse en compras.        |
| `is_sellable`                    | `BOOLEAN`      | NN, DEFAULT `TRUE`  | Indica si puede utilizarse en ventas.         |
| `is_default_purchase`            | `BOOLEAN`      | NN, DEFAULT `FALSE` | Presentación predeterminada para compras.     |
| `is_default_sale`                | `BOOLEAN`      | NN, DEFAULT `FALSE` | Presentación predeterminada para ventas.      |
| `status` | `VARCHAR(20)` | NN, CK, DEFAULT `'ACTIVE'` | Estado dentro de la empresa: `ACTIVE` o `INACTIVE`. |
| `created_by` | `VARCHAR(255)` | NN | `sub` del token de quien crea el registro (Constitución D1); inmutable. |
| `updated_by` | `VARCHAR(255)` | NN | `sub` del token de quien realizó la última modificación (Constitución D1). |
| `version`                        | `INTEGER`      | NN, DEFAULT `1`     | Control concurrente.                          |
| `created_at`                     | `TIMESTAMPTZ`  | NN                  | Fecha de creación.                            |
| `updated_at`                     | `TIMESTAMPTZ`  | NN                  | Última modificación.                          |

### Reglas y restricciones

- La combinación `company_product_id` y `global_product_presentation_id` debe ser única.
- La presentación global debe pertenecer al mismo `GlobalProduct` adoptado por `CompanyProduct`.
- Debe existir como máximo una presentación de compra predeterminada activa por `CompanyProduct`.
- Debe existir como máximo una presentación de venta predeterminada activa por `CompanyProduct`.
- `internal_code` y `sku`, cuando existan, se guardan sin espacios al inicio ni al final, no pueden quedar vacíos y son únicos por empresa sin diferenciar mayúsculas y minúsculas (índices únicos sobre `company_id` y `lower(...)`), en cualquier estado.
- `status` admite `ACTIVE` e `INACTIVE` (`CHECK`); los cambios de estado se hacen con acciones explícitas de inactivar y reactivar, sin eliminar el registro.
- Una presentación inactiva no puede utilizarse en nuevas compras o ventas.
- Desactivar una presentación no modifica documentos históricos.

> **Reconciliación (2026-10-05):** sección alineada con `specs/010-commercial-relationship-commercial-product`
> (Commercial Relationship Fase B): `status` con `CHECK` en lugar de `is_active` (BR-06); auditoría
> `created_by`/`updated_by` con el `sub` en lugar de `created_by_user_id` (BR-07); `internal_code` y `sku`
> únicos por empresa sin diferenciar mayúsculas (BR-09). Los nombres de restricciones e índices están en el
> `data-model.md` de esa feature.

### Relaciones

- Pertenece a un `CompanyProduct`.
- Referencia una `GlobalProductPresentation` de Product Catalog Service.
- Puede ser utilizada por `SupplierProduct`.
- Puede ser utilizada por `PriceListItem`.
- Puede ser referenciada desde `PurchaseDetail` y `SaleDetail`.

## 5.13 PriceList

**Tabla:** `price_lists`

**Naturaleza:** privada por empresa.

**Servicio propietario:** Commercial Relationship Service.

### Descripción

Representa una lista de precios definida por una empresa.

Permite manejar múltiples esquemas de precio como minorista, mayorista, distribuidor, comercio electrónico o cualquier otra estructura comercial sin agregar columnas de precio directamente a `CompanyProduct`.

Las listas encontradas en fuentes externas como `Precio Lista 1` hasta `Precio Lista 18` pueden representarse como registros diferentes de esta entidad.

`PriceList` define la lista y su moneda; los precios concretos de los productos pertenecen a `PriceListItem`.

Durante el MVP, `PriceList` se utiliza únicamente como un mecanismo simple para organizar precios empresariales.

La selección de una lista puede ser explícita o utilizar la lista marcada como predeterminada.

El MVP no implementa motores avanzados para seleccionar automáticamente listas por segmento, volumen, canal, promoción, horario, sucursal u otras reglas comerciales.

Las capacidades avanzadas de resolución de precios pueden incorporarse posteriormente sin modificar la estructura básica de `PriceList` y `PriceListItem`.

### Atributos

| Atributo             | Tipo           | Regla               | Descripción                             |
| -------------------- | -------------- | ------------------- | --------------------------------------- |
| `id`                 | `UUID`         | PK, NN              | Identificador de la lista.              |
| `company_id`         | `UUID`         | REF, NN             | Empresa propietaria.                    |
| `code`               | `VARCHAR(50)`  | NN                  | Código estable de la lista.             |
| `name`               | `VARCHAR(120)` | NN                  | Nombre visible.                         |
| `description`        | `TEXT`         | nullable            | Descripción de su propósito comercial.  |
| `currency_code`      | `CHAR(3)`      | NN                  | Moneda ISO 4217 utilizada por la lista. |
| `is_default`         | `BOOLEAN`      | NN, DEFAULT `FALSE` | Indica si es la lista predeterminada.   |
| `valid_from`         | `TIMESTAMPTZ`  | nullable            | Momento desde el cual puede utilizarse. |
| `valid_to`           | `TIMESTAMPTZ`  | nullable            | Momento hasta el cual puede utilizarse. |
| `status` | `VARCHAR(20)` | NN, CK, DEFAULT `'ACTIVE'` | Estado operativo: `ACTIVE` o `INACTIVE`. |
| `created_by` | `VARCHAR(255)` | NN | `sub` del token de quien crea el registro (Constitución D1); inmutable. |
| `updated_by` | `VARCHAR(255)` | NN | `sub` del token de quien realizó la última modificación (Constitución D1). |
| `version`            | `INTEGER`      | NN, DEFAULT `1`     | Control concurrente.                    |
| `created_at`         | `TIMESTAMPTZ`  | NN                  | Fecha de creación.                      |
| `updated_at`         | `TIMESTAMPTZ`  | NN                  | Última modificación.                    |

### Reglas y restricciones

- La combinación `company_id` y `code` debe ser única sin diferenciar mayúsculas y minúsculas.
- `status` admite `ACTIVE` e `INACTIVE` (`CHECK`); los cambios de estado se hacen con acciones explícitas de inactivar y reactivar, sin eliminar el registro.
- Cuando existan `valid_from` y `valid_to`, `valid_to` debe ser posterior a `valid_from`.
- Debe existir como máximo una lista predeterminada activa por empresa y moneda.
- Una lista inactiva no puede seleccionarse para nuevas ventas.
- Una lista utilizada históricamente no debe eliminarse físicamente.
- La lista no almacena directamente los precios de productos.
- `PriceList` no reemplaza `ProductPricingPolicy`.
- `ProductPricingPolicy` controla reglas de margen y `PriceList` controla precios comerciales.

> **Reconciliación (2026-10-05):** sección alineada con `specs/010-commercial-relationship-commercial-product`
> (Commercial Relationship Fase B): `status` con `CHECK` en lugar de `is_active` (BR-06) y auditoría
> `created_by`/`updated_by` con el `sub` en lugar de `created_by_user_id` (BR-07). Los nombres de
> restricciones e índices están en el `data-model.md` de esa feature.

### Relaciones

- Pertenece a una empresa mediante `company_id`.
- Puede contener múltiples `PriceListItem`.
- Puede ser referenciada desde `SaleDetail` para conservar el origen del precio aplicado.

---

## 5.14 PriceListItem

**Tabla:** `price_list_items`

**Naturaleza:** privada, configurable e histórica por empresa.

**Servicio propietario:** Commercial Relationship Service.

### Descripción

Representa el precio de un producto empresarial dentro de una lista de precios.

Permite establecer precios diferentes para un mismo `CompanyProduct` según la lista comercial seleccionada.

Cuando el producto utiliza varias presentaciones, el precio puede asignarse específicamente a una `CompanyProductPresentation`.

La vigencia permite conservar diferentes versiones históricas de un precio sin sobrescribir la información utilizada en operaciones anteriores.

### Atributos

| Atributo                          | Tipo            | Regla              | Descripción                             |
| --------------------------------- | --------------- | ------------------ | --------------------------------------- |
| `id`                              | `UUID`          | PK, NN             | Identificador del precio.               |
| `company_id`                      | `UUID`          | REF, NN            | Empresa propietaria.                    |
| `price_list_id`                   | `UUID`          | FK, NN             | Lista de precios.                       |
| `company_product_id`              | `UUID`          | FK, NN             | Producto empresarial.                   |
| `company_product_presentation_id` | `UUID`          | FK, nullable       | Presentación empresarial específica.    |
| `unit_price`                      | `NUMERIC(18,4)` | NN                 | Precio unitario configurado.            |
| `valid_from`                      | `TIMESTAMPTZ`   | NN                 | Inicio de vigencia.                     |
| `valid_to`                        | `TIMESTAMPTZ`   | nullable           | Finalización de vigencia.               |
| `status` | `VARCHAR(20)` | NN, CK, DEFAULT `'ACTIVE'` | Estado del precio: `ACTIVE` o `INACTIVE`. |
| `created_by` | `VARCHAR(255)` | NN | `sub` del token de quien crea el registro (Constitución D1); inmutable. |
| `updated_by` | `VARCHAR(255)` | NN | `sub` del token de quien realizó la última modificación (Constitución D1). |
| `version`                         | `INTEGER`       | NN, DEFAULT `1`    | Control concurrente.                    |
| `created_at`                      | `TIMESTAMPTZ`   | NN                 | Fecha de creación.                      |
| `updated_at`                      | `TIMESTAMPTZ`   | NN                 | Última modificación.                    |

### Reglas y restricciones

- `unit_price` no puede ser negativo y admite a lo sumo los decimales de la moneda de la lista; un valor con más decimales se rechaza sin redondear.
- `status` admite `ACTIVE` e `INACTIVE` (`CHECK`); los cambios de estado se hacen con acciones explícitas de inactivar y reactivar, sin eliminar el registro.
- `valid_to` debe ser posterior a `valid_from` cuando exista.
- `price_list_id` debe pertenecer a la misma empresa indicada por `company_id`.
- `company_product_id` debe pertenecer a la misma empresa.
- Cuando exista `company_product_presentation_id`, debe pertenecer al mismo `CompanyProduct`.
- No pueden existir periodos de vigencia solapados entre los precios `ACTIVE` de la misma combinación de lista, producto y presentación.
- `price_list_id`, `company_product_id` y `company_product_presentation_id` son inmutables. `unit_price` y `valid_from` solo se modifican mientras `valid_from` esté en el futuro; un precio en vigencia solo admite fijar, adelantar o posponer `valid_to` a un instante futuro, o inactivarse.
- Para cambiar un precio en vigencia se usa la acción "cambiar precio": en una sola transacción cierra el precio vigente en el instante de efecto y crea uno nuevo para la misma lista, producto y presentación desde ese instante y hasta el `valid_to` que tenía el anterior.
- Si `company_product_presentation_id` es nulo, el precio aplica directamente al `CompanyProduct` de forma general.
- Si `company_product_presentation_id` contiene un valor, el precio aplica exclusivamente a esa presentación empresarial.
- Cuando no exista un `PriceListItem` aplicable, el MVP puede utilizar `CompanyProduct.sale_price` como precio simple o predeterminado según las reglas del proceso de venta.
- La moneda se obtiene desde `PriceList.currency_code`.
- Los precios históricos utilizados en ventas no deben eliminarse físicamente.
- El valor `0` representa un precio real igual a cero; la ausencia de configuración debe representarse mediante la inexistencia de un `PriceListItem`, no mediante un valor cero artificial.

> **Reconciliación (2026-10-05):** sección alineada con `specs/010-commercial-relationship-commercial-product`
> (Commercial Relationship Fase B): `status` con `CHECK` en lugar de `is_active` (BR-06); auditoría
> `created_by`/`updated_by` con el `sub` en lugar de `created_by_user_id` (BR-07); `unit_price` con los
> decimales de la moneda de la lista, precio en vigencia inmutable y acción "cambiar precio" (BR-10). Los
> nombres de restricciones e índices están en el `data-model.md` de esa feature.

### Relaciones

- Pertenece a una `PriceList`.
- Pertenece a un `CompanyProduct`.
- Puede pertenecer a una `CompanyProductPresentation`.
- Puede ser referenciado desde `SaleDetail`.
- Puede coexistir con `CompanyProduct.sale_price`, que funciona como precio simple o de referencia cuando no se utiliza una lista.

---

# 6. Operational Context DB

## 6.1 Company

**Tabla:** `companies`  
**Naturaleza:** privada y aislada.  
**Servicio propietario:** Operational Context Service.

### Descripción

Representa una organización que utiliza SIO como cliente de la plataforma.

Puede relacionarse con su identidad legal global mediante `organization_identity_id`.

La identidad legal, el sector económico asociado y el representante legal se consultan desde Party Identity Service, mientras Operational Context Service sigue siendo propietario del contexto operativo.

La ubicación de `Company` representa su sede principal o administrativa.

Las coordenadas son propias de la sede y no deben sustituirse por el centroide de la ciudad.

### Atributos

| Atributo                     | Tipo           | Regla                        | Descripción                                      |
| ---------------------------- | -------------- | ---------------------------- | ------------------------------------------------ |
| `id`                         | `UUID`         | PK, NN                       | Identificador operativo.                         |
| `organization_identity_id`   | `UUID`         | REF, nullable                | Identidad legal global.                          |
| `identification_type`        | `VARCHAR(20)`  | NN                           | Tipo de identificación.                          |
| `identification_number`      | `VARCHAR(40)`  | NN                           | Número legal.                                    |
| `legal_name`                 | `VARCHAR(200)` | NN                           | Razón social operativa.                          |
| `trade_name`                 | `VARCHAR(200)` | nullable                     | Nombre comercial.                                |
| `email`                      | `VARCHAR(254)` | nullable                     | Correo principal.                                |
| `phone`                      | `VARCHAR(40)`  | nullable                     | Teléfono.                                        |
| `address_line`               | `TEXT`         | nullable                     | Dirección principal.                             |
| `country_id`                 | `UUID`         | REF, nullable                | País administrado por Geography Service.         |
| `administrative_division_id` | `UUID`         | REF, nullable                | Departamento, estado, provincia u otra división. |
| `city_id`                    | `UUID`         | REF, nullable                | Ciudad o municipio.                              |
| `postal_code`                | `VARCHAR(20)`  | nullable                     | Código postal.                                   |
| `latitude`                   | `NUMERIC(9,6)` | nullable                     | Latitud exacta de la sede principal.             |
| `longitude`                  | `NUMERIC(9,6)` | nullable                     | Longitud exacta de la sede principal.            |
| `timezone`                   | `VARCHAR(60)`  | NN, DEFAULT `America/Bogota` | Zona horaria.                                    |
| `default_currency`           | `CHAR(3)`      | NN, DEFAULT `COP`            | Moneda principal.                                |
| `is_active`                  | `BOOLEAN`      | NN, DEFAULT `TRUE`           | Estado.                                          |
| `created_at`                 | `TIMESTAMPTZ`  | NN                           | Creación.                                        |
| `updated_at`                 | `TIMESTAMPTZ`  | NN                           | Modificación.                                    |

### Reglas y restricciones

- La identificación es única.
- Una empresa activa debe completar su vínculo con `OrganizationIdentity` antes de utilizar operaciones que requieran identidad legal verificada.
- La geografía debe ser coherente entre país, división administrativa y ciudad.
- Si existe `latitude`, debe existir `longitude` y viceversa.
- `latitude` debe estar entre `-90` y `90`.
- `longitude` debe estar entre `-180` y `180`.
- El representante legal no se almacena como texto dentro de `Company` se obtiene mediante la identidad legal de la organización y `OrganizationLegalRepresentative`.
- El asesor de la empresa no se almacena únicamente como texto dentro de `Company` se relaciona mediante `CompanyAdvisorAssignment`.
- Una empresa con historia no se elimina físicamente; se desactiva cuando deja de operar.

### Relaciones

- Consulta el sector económico mediante `OrganizationIdentity -> OrganizationBusinessSector`.
- Consulta el representante legal vigente mediante `OrganizationIdentity -> OrganizationLegalRepresentative -> PersonIdentity`.
- Puede tener uno o varios asesores históricos mediante `CompanyAdvisorAssignment -> PersonIdentity`.
- Puede tener muchas sucursales mediante `Branch`.
- Puede tener muchos usuarios operativos mediante `ApplicationUser`.

## 6.2 Branch

**Tabla:** `branches`  
**Naturaleza:** privada por empresa.  
**Servicio propietario:** Operational Context Service.

### Descripción

Representa una sede, tienda, bodega o punto operativo.

El inventario se controla por ubicación, las compras y ventas ocurren en una sucursal y los usuarios reciben asignaciones a sucursales.

Las coordenadas permiten soportar posteriormente logística, distancias, planificación geográfica y modelos de IA.

### Atributos

| Atributo                     | Tipo           | Regla              | Descripción                              |
| ---------------------------- | -------------- | ------------------ | ---------------------------------------- |
| `id`                         | `UUID`         | PK, NN             | Identificador.                           |
| `company_id`                 | `UUID`         | FK, NN             | Empresa.                                 |
| `code`                       | `VARCHAR(40)`  | NN                 | Código interno.                          |
| `name`                       | `VARCHAR(160)` | NN                 | Nombre.                                  |
| `email`                      | `VARCHAR(254)` | nullable           | Correo.                                  |
| `phone`                      | `VARCHAR(40)`  | nullable           | Teléfono.                                |
| `address_line`               | `TEXT`         | nullable           | Dirección.                               |
| `country_id`                 | `UUID`         | REF, nullable      | País administrado por Geography Service. |
| `administrative_division_id` | `UUID`         | REF, nullable      | División administrativa.                 |
| `city_id`                    | `UUID`         | REF, nullable      | Ciudad o municipio.                      |
| `postal_code`                | `VARCHAR(20)`  | nullable           | Código postal.                           |
| `latitude`                   | `NUMERIC(9,6)` | nullable           | Latitud exacta de la sucursal.           |
| `longitude`                  | `NUMERIC(9,6)` | nullable           | Longitud exacta de la sucursal.          |
| `timezone`                   | `VARCHAR(60)`  | nullable           | Zona horaria específica.                 |
| `is_active`                  | `BOOLEAN`      | NN, DEFAULT `TRUE` | Estado.                                  |
| `created_at`                 | `TIMESTAMPTZ`  | NN                 | Creación.                                |
| `updated_at`                 | `TIMESTAMPTZ`  | NN                 | Modificación.                            |

### Reglas y restricciones

- `code` es único dentro de la empresa.
- La geografía debe ser coherente entre país, división y ciudad.
- Si existe una coordenada debe existir la otra.
- `latitude` debe estar entre `-90` y `90`.
- `longitude` entre `-180` y `180`.

## 6.3 ApplicationUser

**Tabla:** `application_users`  
**Naturaleza:** privada por empresa.  
**Servicio propietario:** Operational Context Service.

### Descripción

Representa el perfil operativo de una persona autenticada por Keycloak.

Keycloak conserva credenciales, roles, sesiones y tokens.

SIO conserva la empresa del usuario, su estado operativo, sus sucursales y el identificador usado en documentos y auditoría.

La relación se realiza mediante el claim `sub` de Keycloak.

### Atributos

| Atributo           | Tipo           | Regla              | Descripción                        |
| ------------------ | -------------- | ------------------ | ---------------------------------- |
| `id`               | `UUID`         | PK, NN             | Identificador operativo.           |
| `keycloak_user_id` | `UUID`         | NN, UQ             | Identificador estable en Keycloak. |
| `company_id`       | `UUID`         | FK, NN             | Empresa.                           |
| `display_name`     | `VARCHAR(160)` | NN                 | Nombre de referencia.              |
| `reference_email`  | `VARCHAR(254)` | nullable           | Correo de referencia.              |
| `is_active`        | `BOOLEAN`      | NN, DEFAULT `TRUE` | Estado en SIO.                     |
| `created_at`       | `TIMESTAMPTZ`  | NN                 | Creación.                          |
| `updated_at`       | `TIMESTAMPTZ`  | NN                 | Modificación.                      |

## 6.4 UserBranch

**Tabla:** `user_branches`  
**Naturaleza:** privada por empresa.  
**Servicio propietario:** Operational Context Service.

### Descripción

Resuelve la relación muchos a muchos entre usuarios y sucursales.

Para operar no basta con tener un rol ya que también se requiere que el usuario esté activo y tenga asignada la sucursal correspondiente.

### Atributos

| Atributo              | Tipo          | Regla              | Descripción             |
| --------------------- | ------------- | ------------------ | ----------------------- |
| `id`                  | `UUID`        | PK, NN             | Identificador.          |
| `application_user_id` | `UUID`        | FK, NN             | Usuario.                |
| `branch_id`           | `UUID`        | FK, NN             | Sucursal.               |
| `is_active`           | `BOOLEAN`     | NN, DEFAULT `TRUE` | Estado.                 |
| `assigned_at`         | `TIMESTAMPTZ` | NN                 | Fecha de asignación.    |
| `assigned_by_user_id` | `UUID`        | FK, NN             | Usuario asignador.      |
| `deactivated_at`      | `TIMESTAMPTZ` | nullable           | Fecha de desactivación. |

### Reglas y restricciones

- La combinación usuario-sucursal es única.

## 6.5 CompanyAdvisorAssignment

**Tabla:** `company_advisor_assignments`  
**Naturaleza:** privada, histórica y operacional.  
**Servicio propietario:** Operational Context Service.

### Descripción

Representa la relación histórica entre una empresa registrada en SIO y la persona que actúa como su asesor.

El asesor pertenece al contexto de la empresa y no representa un usuario interno de la plataforma SIO.

La identidad de la persona se administra mediante `PersonIdentity` permitiendo evitar registrar únicamente el nombre del asesor como texto libre y posibilitando reutilizar la misma identidad cuando una persona desempeñe otros roles dentro del ecosistema.

La relación se mantiene separada de `Company` porque el asesor puede cambiar con el tiempo.

Cuando una empresa cambia de asesor la asignación anterior no se sobrescribe ni se elimina, su vigencia se cierra mediante `valid_to` y se crea una nueva asignación.

Esto permite conocer tanto el asesor vigente como los asesores que estuvieron relacionados anteriormente con la empresa.

El asesor no necesita obligatoriamente tener una cuenta de usuario en SIO.

Si además utiliza la aplicación su acceso se administra independientemente mediante `ApplicationUser` y Keycloak.

### Atributos

| Atributo              | Tipo          | Regla              | Descripción                                                                |
| --------------------- | ------------- | ------------------ | -------------------------------------------------------------------------- |
| `id`                  | `UUID`        | PK, NN             | Identificador único de la asignación.                                      |
| `company_id`          | `UUID`        | FK, NN             | Empresa a la que pertenece la asignación del asesor.                       |
| `person_identity_id`  | `UUID`        | REF, NN            | Identidad global de la persona que actúa como asesor.                      |
| `is_primary`          | `BOOLEAN`     | NN, DEFAULT `TRUE` | Indica si la persona es el asesor principal vigente de la empresa.         |
| `is_active`           | `BOOLEAN`     | NN, DEFAULT `TRUE` | Indica si la asignación se encuentra vigente.                              |
| `valid_from`          | `TIMESTAMPTZ` | NN                 | Momento desde el cual inicia la asignación.                                |
| `valid_to`            | `TIMESTAMPTZ` | nullable           | Momento hasta el cual estuvo vigente y es nulo para una asignación activa. |
| `assigned_by_user_id` | `UUID`        | FK, nullable       | Usuario operativo que registró la asignación cuando aplique.               |
| `created_at`          | `TIMESTAMPTZ` | NN                 | Fecha de creación del registro.                                            |
| `updated_at`          | `TIMESTAMPTZ` | NN                 | Última modificación permitida sobre estado o vigencia.                     |

### Reglas y restricciones

- `person_identity_id` referencia una `PersonIdentity` administrada por Party Identity Service y no utiliza una llave foránea física entre bases de datos.
- La persona debe existir y encontrarse disponible para nuevas relaciones al momento de crear la asignación.
- Debe existir como máximo un asesor principal activo por empresa.
- Una asignación activa debe cumplir:

```text
is_active = TRUE
valid_to = NULL
```

- Una asignación histórica debe cumplir:

```text
is_active = FALSE
valid_to IS NOT NULL
```

- Cuando `valid_to` exista debe ser mayor que `valid_from`.
- Una asignación histórica no se elimina físicamente.
- Cuando cambia el asesor principal la asignación vigente debe cerrarse y debe crearse una nueva asignación.
- El cierre de la asignación anterior y la creación de la nueva deben realizarse dentro de una misma transacción local cuando ambas operaciones pertenezcan al mismo proceso.
- El nombre del asesor no se copia como fuente oficial dentro de `Company`.
- La información personal del asesor pertenece a `PersonIdentity` y a su perfil de contacto correspondiente.
- Ser asesor de una empresa no implica necesariamente tener credenciales ni acceso operativo a SIO.

### Cambio de asesor

Si durante un período la empresa tiene:

```text
Empresa ABC
    ↓
Juan Pérez

valid_from = 2026-01-01
valid_to   = NULL
is_active  = TRUE
```

y posteriormente María Gómez se convierte en la nueva asesora, SIO debe cerrar la relación anterior:

```text
Juan Pérez

valid_from = 2026-01-01
valid_to   = 2026-08-11
is_active  = FALSE
```

y crear:

```text
María Gómez

valid_from = 2026-08-11
valid_to   = NULL
is_active  = TRUE
```

De esta manera se conserva el historial de asesores relacionados con la empresa.

### Relaciones

- Pertenece a una única `Company`.
- Referencia una única `PersonIdentity`.
- Una `Company` puede tener múltiples asignaciones históricas de asesores.
- Una `PersonIdentity` puede actuar como asesor de una o varias empresas cuando las reglas del negocio lo permitan.
- La identidad, nombre y datos personales del asesor se consultan desde Party Identity Service.
- Si el asesor además posee acceso a SIO para dicha autenticación y operación se administran independientemente mediante `ApplicationUser` y Keycloak.

# 7. Purchase DB

## 7.1 Purchase

**Tabla:** `purchases`  
**Naturaleza:** transaccional y privada.  
**Servicio propietario:** Purchase Service.

### Descripción

Representa la cabecera de una compra.

Comienza en `DRAFT` y no afecta inventario.

Al confirmar se validan proveedor y productos se coordina con Inventory Service, se aplican todas las entradas y se asigna el número oficial.

Si algo falla la compra no queda confirmada parcialmente.

### Atributos

| Atributo                           | Tipo            | Regla                | Descripción                                                 |
| ---------------------------------- | --------------- | -------------------- | ----------------------------------------------------------- |
| `id`                               | `UUID`          | PK, NN               | Identificador.                                              |
| `company_id`                       | `UUID`          | REF, NN              | Empresa.                                                    |
| `branch_id`                        | `UUID`          | REF, NN              | Sucursal.                                                   |
| `company_supplier_id`              | `UUID`          | REF, NN              | Proveedor privado.                                          |
| `supplier_payment_condition_id`    | `UUID`          | REF, nullable        | Condición comercial seleccionada del proveedor.             |
| `payment_condition_code_snapshot`  | `VARCHAR(30)`   | NN                   | Snapshot `CASH`, `CREDIT` o `FINANCING`.                    |
| `payment_terms_days_snapshot`      | `INTEGER`       | NN, DEFAULT `0`      | Plazo pactado al confirmar la compra.                       |
| `due_date`                         | `DATE`          | NN                   | Fecha de exigibilidad usada por Finance Service.            |
| `purchase_sequence_id`             | `UUID`          | FK, nullable         | Secuencia usada.                                            |
| `number`                           | `VARCHAR(80)`   | UQ parcial, nullable | Número oficial.                                             |
| `sequence_value`                   | `BIGINT`        | nullable             | Parte numérica.                                             |
| `status`                           | `VARCHAR(20)`   | NN, CK               | `DRAFT`, `CONFIRMED` o `CANCELLED`.                         |
| `operation_date`                   | `DATE`          | NN                   | Fecha de negocio.                                           |
| `promised_delivery_at`             | `TIMESTAMPTZ`   | nullable             | Fecha/hora de entrega comprometida al formalizar el pedido. |
| `supplier_document_number`         | `VARCHAR(100)`  | nullable             | Documento del proveedor.                                    |
| `supplier_name_snapshot`           | `VARCHAR(200)`  | NN                   | Nombre histórico.                                           |
| `supplier_identification_snapshot` | `VARCHAR(100)`  | NN                   | Identificación histórica.                                   |
| `currency_code`                    | `CHAR(3)`       | NN                   | Moneda.                                                     |
| `observations`                     | `TEXT`          | nullable             | Observaciones.                                              |
| `subtotal`                         | `NUMERIC(18,2)` | NN                   | Subtotal.                                                   |
| `discount_total`                   | `NUMERIC(18,2)` | NN                   | Descuentos.                                                 |
| `tax_total`                        | `NUMERIC(18,2)` | NN                   | Impuestos.                                                  |
| `total`                            | `NUMERIC(18,2)` | NN                   | Total final.                                                |
| `created_by_user_id`               | `UUID`          | REF, NN              | Usuario creador.                                            |
| `cancelled_by_user_id`             | `UUID`          | REF, nullable        | Usuario que anuló.                                          |
| `cancelled_at`                     | `TIMESTAMPTZ`   | nullable             | Anulación.                                                  |
| `cancellation_reason`              | `TEXT`          | nullable             | Motivo.                                                     |
| `version`                          | `INTEGER`       | NN, DEFAULT `1`      | Control concurrente.                                        |
| `created_at`                       | `TIMESTAMPTZ`   | NN                   | Creación.                                                   |
| `updated_at`                       | `TIMESTAMPTZ`   | NN                   | Modificación.                                               |

### Reglas financieras

- La condición seleccionada debe pertenecer al mismo `CompanySupplier` y estar activa al confirmar la compra.
- Para `CASH`, `payment_terms_days_snapshot = 0` y `due_date` corresponde a la fecha de negocio definida por la política operativa.
- Para `CREDIT` o `FINANCING`, `due_date` se calcula a partir del plazo pactado y se conserva como snapshot histórico.
- Al confirmar la compra `Purchase Service` publica el hecho necesario para que Finance Service cree o actualice la obligación correspondiente.
- `Purchase Service` no administra el saldo de cartera.

## 7.2 PurchaseDetail

**Tabla:** `purchase_details`  
**Naturaleza:** transaccional y privada.  
**Servicio propietario:** Purchase Service.

### Descripción

Representa una línea de compra.

Conserva producto, cantidad, costo, descuentos, impuestos y total.

Los snapshots del producto garantizan que el documento histórico no cambie si el catálogo se modifica después.

### Atributos

| Atributo                            | Tipo            | Regla           | Descripción                                                                                   |
| ----------------------------------- | --------------- | --------------- | --------------------------------------------------------------------------------------------- |
| `id`                                | `UUID`          | PK, NN          | Identificador.                                                                                |
| `purchase_id`                       | `UUID`          | FK, NN          | Compra.                                                                                       |
| `line_number`                       | `SMALLINT`      | NN              | Posición.                                                                                     |
| `company_product_id`                | `UUID`          | REF, NN         | Producto empresarial.                                                                         |
| `company_product_presentation_id`   | `UUID`          | REF, nullable   | Presentación empresarial utilizada en la compra.                                              |
| `supplier_product_id`               | `UUID`          | REF, nullable   | Relación comercial proveedor-producto utilizada.                                              |
| `supplier_lead_time_snapshot_hours` | `NUMERIC(12,2)` | nullable        | Lead time esperado del proveedor conservado al formalizar la línea.                           |
| `product_code_snapshot`             | `VARCHAR(80)`   | NN              | Código histórico.                                                                             |
| `product_name_snapshot`             | `VARCHAR(200)`  | NN              | Nombre histórico.                                                                             |
| `presentation_code_snapshot`        | `VARCHAR(80)`   | nullable        | Código histórico de la presentación utilizada.                                                |
| `presentation_name_snapshot`        | `VARCHAR(160)`  | nullable        | Nombre histórico de la presentación utilizada.                                                |
| `base_quantity_factor_snapshot`     | `NUMERIC(18,8)` | NN, DEFAULT `1` | Factor histórico utilizado para convertir la cantidad comprada a la unidad base del producto. |
| `unit_code_snapshot`                | `VARCHAR(20)`   | NN              | Unidad histórica.                                                                             |
| `quantity`                          | `NUMERIC(18,4)` | NN              | Cantidad.                                                                                     |
| `unit_cost`                         | `NUMERIC(18,4)` | NN              | Costo unitario.                                                                               |
| `discount_amount`                   | `NUMERIC(18,2)` | NN, DEFAULT `0` | Descuento.                                                                                    |
| `tax_amount`                        | `NUMERIC(18,2)` | NN, DEFAULT `0` | Impuesto.                                                                                     |
| `subtotal`                          | `NUMERIC(18,2)` | NN              | Subtotal.                                                                                     |
| `total`                             | `NUMERIC(18,2)` | NN              | Total.                                                                                        |
| `created_at`                        | `TIMESTAMPTZ`   | NN              | Creación.                                                                                     |
| `updated_at`                        | `TIMESTAMPTZ`   | NN              | Modificación.                                                                                 |

### Reglas y restricciones

- El número de línea es único dentro de la compra.
- Cantidad mayor que cero.
- Valores monetarios no negativos.
- Cuando exista `company_product_presentation_id`, debe pertenecer al mismo `CompanyProduct` indicado por `company_product_id`.
- `base_quantity_factor_snapshot` debe ser mayor que cero.
- La confirmación de la compra debe convertir la cantidad adquirida a la unidad base utilizando `base_quantity_factor_snapshot` antes de generar el movimiento de inventario.
- Los snapshots de presentación no deben modificarse aunque posteriormente cambie la definición de la presentación empresarial o global.

## 7.3 PurchaseSequence

**Tabla:** `purchase_sequences`  
**Naturaleza:** configuración transaccional privada.  
**Servicio propietario:** Purchase Service.

### Descripción

Controla exclusivamente la numeración oficial de documentos de compras.

La secuencia se actualiza atómicamente para evitar números duplicados.

El frontend no decide el número ya que la configuración puede variar por empresa, sucursal, tipo documental y serie.

### Atributos

| Atributo         | Tipo          | Regla              | Descripción                    |
| ---------------- | ------------- | ------------------ | ------------------------------ |
| `id`             | `UUID`        | PK, NN             | Identificador.                 |
| `company_id`     | `UUID`        | REF, NN            | Empresa.                       |
| `branch_id`      | `UUID`        | REF, nullable      | Sucursal.                      |
| `document_kind`  | `VARCHAR(40)` | NN                 | Tipo documental.               |
| `series_code`    | `VARCHAR(40)` | NN                 | Serie.                         |
| `prefix`         | `VARCHAR(20)` | NN                 | Prefijo.                       |
| `separator`      | `VARCHAR(5)`  | NN                 | Separador.                     |
| `current_number` | `BIGINT`      | NN                 | Último número usado.           |
| `initial_number` | `BIGINT`      | NN                 | Número inicial.                |
| `maximum_number` | `BIGINT`      | nullable           | Máximo.                        |
| `number_length`  | `SMALLINT`    | NN                 | Cantidad de dígitos.           |
| `reset_policy`   | `VARCHAR(20)` | NN, CK             | `NEVER`, `YEARLY` o `MONTHLY`. |
| `last_reset_at`  | `TIMESTAMPTZ` | nullable           | Último reinicio.               |
| `is_active`      | `BOOLEAN`     | NN, DEFAULT `TRUE` | Estado.                        |
| `version`        | `INTEGER`     | NN, DEFAULT `1`    | Control concurrente.           |
| `created_at`     | `TIMESTAMPTZ` | NN                 | Creación.                      |
| `updated_at`     | `TIMESTAMPTZ` | NN                 | Modificación.                  |

## 7.4 PurchaseOperation

**Tabla:** `purchase_operations`  
**Naturaleza:** coordinación técnica y funcional.  
**Servicio propietario:** Purchase Service.

### Descripción

Sigue una confirmación o anulación distribuida.

Compra e inventario están en bases diferentes por lo que no existe una sola transacción PostgreSQL.

Esta entidad permite saber si la operación está pendiente, fue completada o falló y evita confirmaciones duplicadas.

### Atributos

| Atributo          | Tipo           | Regla    | Descripción                        |
| ----------------- | -------------- | -------- | ---------------------------------- |
| `id`              | `UUID`         | PK, NN   | Identificador de operación.        |
| `company_id`      | `UUID`         | REF, NN  | Empresa.                           |
| `purchase_id`     | `UUID`         | FK, NN   | Compra.                            |
| `operation_type`  | `VARCHAR(20)`  | NN, CK   | `CONFIRM` o `CANCEL`.              |
| `idempotency_key` | `VARCHAR(150)` | NN, UQ   | Clave idempotente.                 |
| `status`          | `VARCHAR(20)`  | NN, CK   | `PENDING`, `SUCCEEDED` o `FAILED`. |
| `correlation_id`  | `UUID`         | NN       | Flujo distribuido.                 |
| `error_code`      | `VARCHAR(100)` | nullable | Código de error.                   |
| `error_details`   | `JSONB`        | nullable | Detalle.                           |
| `started_at`      | `TIMESTAMPTZ`  | NN       | Inicio.                            |
| `updated_at`      | `TIMESTAMPTZ`  | NN       | Actualización.                     |
| `completed_at`    | `TIMESTAMPTZ`  | nullable | Finalización.                      |

## 7.5 PurchaseLifecycleEvent

**Tabla:** `purchase_lifecycle_events`  
**Naturaleza:** histórica, privada e inmutable.  
**Servicio propietario:** Purchase Service.

### Descripción

Representa cada hito importante que ocurre durante el ciclo de vida logístico de una compra especialmente los momentos que necesitamos registrar para calcular tiempos reales de abastecimiento, recepción y procesamiento

Los hitos iniciales son:

- `ORDERED`: pedido enviado o formalizado con el proveedor.
- `SUPPLIER_DISPATCHED`: proveedor informa o registra despacho.
- `ARRIVED`: mercancía llega al punto de recepción.
- `RECEIVED`: mercancía es recibida y validada.
- `AVAILABLE_FOR_SALE`: mercancía queda disponible para uso o venta.

### Atributos

| Atributo              | Tipo          | Regla    | Descripción                                   |
| --------------------- | ------------- | -------- | --------------------------------------------- |
| `id`                  | `UUID`        | PK, NN   | Identificador.                                |
| `company_id`          | `UUID`        | REF, NN  | Empresa.                                      |
| `purchase_id`         | `UUID`        | FK, NN   | Compra.                                       |
| `event_type`          | `VARCHAR(40)` | NN, CK   | Tipo de hito.                                 |
| `occurred_at`         | `TIMESTAMPTZ` | NN       | Momento real del hito.                        |
| `recorded_by_user_id` | `UUID`        | REF, NN  | Usuario que registró o confirmó el hito.      |
| `source`              | `VARCHAR(30)` | NN, CK   | `USER`, `SUPPLIER`, `INTEGRATION` o `SYSTEM`. |
| `notes`               | `TEXT`        | nullable | Observaciones.                                |
| `created_at`          | `TIMESTAMPTZ` | NN       | Persistencia del evento.                      |

### Reglas y restricciones

- Los eventos son inmutables.
- Un error se corrige mediante un nuevo evento de corrección definido por la política funcional y no editando el histórico.
- Debe impedirse una secuencia temporal imposible entre hitos válidos.
- Para el cálculo estándar, el lead time total se obtiene entre `ORDERED` y `AVAILABLE_FOR_SALE`.
- El lead time del proveedor para tiempo logístico, recepción y procesamiento interno se derivan de los intervalos entre hitos.
- El lead time real nunca sobrescribe `SupplierProduct.expected_supplier_lead_time_hours`.

# 8. Sales DB

## 8.1 Sale

**Tabla:** `sales`  
**Naturaleza:** transaccional y privada.  
**Servicio propietario:** Sales Service.

### Descripción

Representa la cabecera de una venta.

Relaciona empresa, sucursal y cliente privado.

Conserva totales, estado, consecutivo, snapshots del cliente y usuarios responsables.

Comienza en `DRAFT` y no descuenta inventario.

Al confirmar, Inventory Service valida saldo y aplica todas las salidas.

Si una línea no tiene disponibilidad y se rechaza toda la confirmación.

### Atributos

| Atributo                           | Tipo            | Regla                | Descripción                                       |
| ---------------------------------- | --------------- | -------------------- | ------------------------------------------------- |
| `id`                               | `UUID`          | PK, NN               | Identificador.                                    |
| `company_id`                       | `UUID`          | REF, NN              | Empresa.                                          |
| `branch_id`                        | `UUID`          | REF, NN              | Sucursal.                                         |
| `company_customer_id`              | `UUID`          | REF, NN              | Cliente privado.                                  |
| `customer_payment_condition_id`    | `UUID`          | REF, nullable        | Condición de compra seleccionada para el cliente. |
| `payment_condition_code_snapshot`  | `VARCHAR(30)`   | NN                   | Snapshot `CASH`, `CREDIT` o `FINANCING`.          |
| `payment_terms_days_snapshot`      | `INTEGER`       | NN, DEFAULT `0`      | Plazo concedido al confirmar la venta.            |
| `due_date`                         | `DATE`          | NN                   | Fecha de exigibilidad usada por Finance Service.  |
| `sale_sequence_id`                 | `UUID`          | FK, nullable         | Secuencia.                                        |
| `number`                           | `VARCHAR(80)`   | UQ parcial, nullable | Número oficial.                                   |
| `sequence_value`                   | `BIGINT`        | nullable             | Parte numérica.                                   |
| `status`                           | `VARCHAR(20)`   | NN, CK               | `DRAFT`, `CONFIRMED` o `CANCELLED`.               |
| `operation_date`                   | `DATE`          | NN                   | Fecha.                                            |
| `customer_name_snapshot`           | `VARCHAR(200)`  | NN                   | Nombre histórico.                                 |
| `customer_identification_snapshot` | `VARCHAR(100)`  | NN                   | Identificación histórica.                         |
| `currency_code`                    | `CHAR(3)`       | NN                   | Moneda.                                           |
| `observations`                     | `TEXT`          | nullable             | Observaciones.                                    |
| `subtotal`                         | `NUMERIC(18,2)` | NN                   | Subtotal.                                         |
| `discount_total`                   | `NUMERIC(18,2)` | NN                   | Descuentos.                                       |
| `tax_total`                        | `NUMERIC(18,2)` | NN                   | Impuestos.                                        |
| `total`                            | `NUMERIC(18,2)` | NN                   | Total.                                            |
| `created_by_user_id`               | `UUID`          | REF, NN              | Usuario creador.                                  |
| `cancelled_by_user_id`             | `UUID`          | REF, nullable        | Usuario que anuló.                                |
| `cancelled_at`                     | `TIMESTAMPTZ`   | nullable             | Anulación.                                        |
| `cancellation_reason`              | `TEXT`          | nullable             | Motivo.                                           |
| `version`                          | `INTEGER`       | NN, DEFAULT `1`      | Control concurrente.                              |
| `created_at`                       | `TIMESTAMPTZ`   | NN                   | Creación.                                         |
| `updated_at`                       | `TIMESTAMPTZ`   | NN                   | Modificación.                                     |

### Reglas financieras

- La condición seleccionada debe pertenecer al mismo `CompanyCustomer` y estar activa al confirmar la venta.
- Para `CREDIT` o `FINANCING` se debe validar el `CustomerCreditProfile` su riesgo, cupo y plazo autorizado.
- Para `CASH`, `payment_terms_days_snapshot = 0`.
- La condición de pago no determina el medio de pago, los recaudos reales se registran en `Finance Service`.
- Al confirmar la venta `Sales Service` publica el hecho necesario para crear la cuenta por cobrar correspondiente.
- `Sales Service` no administra cartera.

## 8.2 SaleDetail

**Tabla:** `sale_details`  
**Naturaleza:** transaccional y privada.  
**Servicio propietario:** Sales Service.

### Descripción

Representa cada producto vendido o contiene el desglose de lo vendido.

Conserva cantidad, precio, descuentos, impuestos y snapshots.

El precio histórico no cambia cuando se modifica el precio actual del producto empresarial.

### Atributos

| Atributo                          | Tipo            | Regla           | Descripción                                                                                  |
| --------------------------------- | --------------- | --------------- | -------------------------------------------------------------------------------------------- |
| `id`                              | `UUID`          | PK, NN          | Identificador.                                                                               |
| `sale_id`                         | `UUID`          | FK, NN          | Venta.                                                                                       |
| `line_number`                     | `SMALLINT`      | NN              | Número de línea.                                                                             |
| `company_product_id`              | `UUID`          | REF, NN         | Producto empresarial.                                                                        |
| `company_product_presentation_id` | `UUID`          | REF, nullable   | Presentación empresarial utilizada en la venta.                                              |
| `price_list_id`                   | `UUID`          | REF, nullable   | Lista de precios utilizada para determinar el precio cuando aplique.                         |
| `price_list_item_id`              | `UUID`          | REF, nullable   | Precio configurado de la lista utilizado como referencia cuando aplique.                     |
| `product_code_snapshot`           | `VARCHAR(80)`   | NN              | Código histórico.                                                                            |
| `product_name_snapshot`           | `VARCHAR(200)`  | NN              | Nombre histórico.                                                                            |
| `presentation_code_snapshot`      | `VARCHAR(80)`   | nullable        | Código histórico de la presentación vendida.                                                 |
| `presentation_name_snapshot`      | `VARCHAR(160)`  | nullable        | Nombre histórico de la presentación vendida.                                                 |
| `base_quantity_factor_snapshot`   | `NUMERIC(18,8)` | NN, DEFAULT `1` | Factor histórico utilizado para convertir la cantidad vendida a la unidad base del producto. |
| `unit_code_snapshot`              | `VARCHAR(20)`   | NN              | Unidad histórica.                                                                            |
| `quantity`                        | `NUMERIC(18,4)` | NN              | Cantidad.                                                                                    |
| `unit_price`                      | `NUMERIC(18,4)` | NN              | Precio unitario.                                                                             |
| `unit_cost_snapshot`              | `NUMERIC(18,4)` | nullable        | Costo unitario histórico aplicado al confirmar.                                              |
| `cost_total`                      | `NUMERIC(18,2)` | nullable        | Costo total histórico de la línea.                                                           |
| `gross_margin_amount`             | `NUMERIC(18,2)` | nullable        | Margen bruto monetario de la línea.                                                          |
| `gross_margin_percentage`         | `NUMERIC(7,4)`  | nullable        | Margen bruto porcentual sobre venta neta.                                                    |
| `discount_amount`                 | `NUMERIC(18,2)` | NN, DEFAULT `0` | Descuento.                                                                                   |
| `tax_amount`                      | `NUMERIC(18,2)` | NN, DEFAULT `0` | Impuesto.                                                                                    |
| `subtotal`                        | `NUMERIC(18,2)` | NN              | Subtotal.                                                                                    |
| `total`                           | `NUMERIC(18,2)` | NN              | Total.                                                                                       |
| `created_at`                      | `TIMESTAMPTZ`   | NN              | Creación.                                                                                    |
| `updated_at`                      | `TIMESTAMPTZ`   | NN              | Modificación.                                                                                |

### Reglas y restricciones

- El número de línea es único dentro de la venta.
- Cantidad mayor que cero.
- Valores monetarios no negativos.
- `unit_cost_snapshot`, `cost_total` y los márgenes se completan al confirmar la venta con el costo informado por `Inventory Service`.
- Una venta histórica no recalcula sus márgenes cuando cambia `CompanyProduct.reference_cost`.
- Cuando exista `company_product_presentation_id`, debe pertenecer al mismo `CompanyProduct` indicado por `company_product_id`.
- `base_quantity_factor_snapshot` debe ser mayor que cero.
- La validación y salida de inventario debe realizarse en la unidad base utilizando `base_quantity_factor_snapshot`.
- `price_list_id` y `price_list_item_id` son referencias externas a Commercial Relationship Service y no utilizan llaves foráneas físicas.
- Cuando exista `price_list_item_id`, debe corresponder a la misma `price_list_id`, producto y presentación utilizados por la línea.
- `unit_price` representa el precio histórico definitivo de la venta y no debe recalcularse posteriormente aunque cambie la lista de precios.

## 8.3 SaleSequence

**Tabla:** `sale_sequences`  
**Naturaleza:** configuración transaccional privada.  
**Servicio propietario:** Sales Service.

### Descripción

Controla exclusivamente la numeración de ventas.

Su separación de compras permite incorporar después cotizaciones, pedidos, facturas y notas crédito sin afectar Purchase Service.

Tiene la misma estructura técnica que `PurchaseSequence`.

### Atributos

| Atributo         | Tipo          | Regla              | Descripción          |
| ---------------- | ------------- | ------------------ | -------------------- |
| `id`             | `UUID`        | PK, NN             | Identificador.       |
| `company_id`     | `UUID`        | REF, NN            | Empresa.             |
| `branch_id`      | `UUID`        | REF, nullable      | Sucursal.            |
| `document_kind`  | `VARCHAR(40)` | NN                 | Tipo documental.     |
| `series_code`    | `VARCHAR(40)` | NN                 | Serie.               |
| `prefix`         | `VARCHAR(20)` | NN                 | Prefijo.             |
| `separator`      | `VARCHAR(5)`  | NN                 | Separador.           |
| `current_number` | `BIGINT`      | NN                 | Último número.       |
| `initial_number` | `BIGINT`      | NN                 | Número inicial.      |
| `maximum_number` | `BIGINT`      | nullable           | Máximo.              |
| `number_length`  | `SMALLINT`    | NN                 | Dígitos.             |
| `reset_policy`   | `VARCHAR(20)` | NN, CK             | Política.            |
| `last_reset_at`  | `TIMESTAMPTZ` | nullable           | Reinicio.            |
| `is_active`      | `BOOLEAN`     | NN, DEFAULT `TRUE` | Estado.              |
| `version`        | `INTEGER`     | NN, DEFAULT `1`    | Control concurrente. |
| `created_at`     | `TIMESTAMPTZ` | NN                 | Creación.            |
| `updated_at`     | `TIMESTAMPTZ` | NN                 | Modificación.        |

## 8.4 SaleOperation

**Tabla:** `sale_operations`  
**Naturaleza:** coordinación técnica y funcional.  
**Servicio propietario:** Sales Service.

### Descripción

Sigue la confirmación o anulación distribuida de una venta.

Permite saber si inventario aplicó salidas, rechazó la operación por saldo insuficiente, aplicó un reverso o encontró un error.

La idempotencia evita descontar dos veces por reintentos.

### Atributos

| Atributo          | Tipo           | Regla    | Descripción           |
| ----------------- | -------------- | -------- | --------------------- |
| `id`              | `UUID`         | PK, NN   | Identificador.        |
| `company_id`      | `UUID`         | REF, NN  | Empresa.              |
| `sale_id`         | `UUID`         | FK, NN   | Venta.                |
| `operation_type`  | `VARCHAR(20)`  | NN, CK   | `CONFIRM` o `CANCEL`. |
| `idempotency_key` | `VARCHAR(150)` | NN, UQ   | Clave idempotente.    |
| `status`          | `VARCHAR(20)`  | NN, CK   | Estado.               |
| `correlation_id`  | `UUID`         | NN       | Flujo.                |
| `error_code`      | `VARCHAR(100)` | nullable | Código.               |
| `error_details`   | `JSONB`        | nullable | Detalle.              |
| `started_at`      | `TIMESTAMPTZ`  | NN       | Inicio.               |
| `updated_at`      | `TIMESTAMPTZ`  | NN       | Actualización.        |
| `completed_at`    | `TIMESTAMPTZ`  | nullable | Finalización.         |

# 9. Inventory DB

## 9.1 InventoryBalance

**Tabla:** `inventory_balances`  
**Naturaleza:** privada por empresa y sucursal.  
**Servicio propietario:** Inventory Service.

### Descripción

Representa la cantidad actual disponible de un producto en una sucursal específica y su valor FIFO.

Es la tabla que SIO consulta cuando necesita saber rápidamente cuánto inventario hay en este momento.

Es una vista persistida del saldo vigente para consultas rápidas.

No explica cómo se llegó al valor y la historia completa pertenece a `InventoryMovement`; el detalle del costo pertenece a `InventoryCostLayer`.

### Atributos

| Atributo             | Tipo            | Regla                    | Descripción                                                                 |
| -------------------- | --------------- | ------------------------ | --------------------------------------------------------------------------- |
| `id`                 | `UUID`          | PK, NN                   | Identificador.                                                              |
| `company_id`         | `UUID`          | REF, NN                  | Empresa.                                                                    |
| `branch_id`          | `UUID`          | REF, NN                  | Sucursal.                                                                   |
| `company_product_id` | `UUID`          | REF, NN                  | Producto empresarial.                                                       |
| `quantity`           | `NUMERIC(18,4)` | NN, DEFAULT `0`, CK      | Saldo actual en unidad base; nunca negativo.                                |
| `version`            | `INTEGER`       | NN, DEFAULT `0`, CK      | Número de movimientos aplicados; igual al `balance_sequence` del último.    |
| `created_at`         | `TIMESTAMPTZ`   | NN                       | Creación (primer movimiento).                                               |
| `created_by`         | `VARCHAR(255)`  | NN                       | `sub` de quien aplicó el primer movimiento: cuenta de servicio en entradas, salidas y reversos; usuario en ajustes y conteos (D1). |
| `updated_at`         | `TIMESTAMPTZ`   | NN                       | Último movimiento.                                                          |
| `updated_by`         | `VARCHAR(255)`  | NN                       | `sub` de quien aplicó el último movimiento (D1).                            |
| `average_unit_cost`  | `NUMERIC(18,4)` | nullable                 | `inventory_value / quantity` con 4 decimales; nulo con saldo 0. Informativo. |
| `inventory_value`    | `NUMERIC(18,2)` | NN, DEFAULT `0`, CK      | Valor FIFO del saldo: Σ `round(remaining_quantity × unit_cost, 2)` de sus capas abiertas, recalculado (no acumulado) en cada movimiento; no negativo. |
| `has_unknown_cost`   | `BOOLEAN`       | NN, DEFAULT `false`      | Alguna capa abierta del saldo no tiene costo histórico (`cost_known = false`). |

### Reglas y restricciones

- Solo existe un saldo por empresa, sucursal y producto.
- El saldo nunca es negativo (`CHECK quantity >= 0`); una operación que lo dejaría negativo se rechaza completa.
- Cantidad, `version` y valor se actualizan únicamente por Inventory Service, con la fila bloqueada (`SELECT … FOR UPDATE`) dentro de la transacción del movimiento.
- La cantidad del saldo es siempre la suma de `remaining_quantity` de sus capas abiertas, y su valor la suma del valor de esas capas; se verifica antes de confirmar cada operación y, si no se cumple, la operación se revierte completa.
- El saldo nace con el primer movimiento y nunca se elimina (la base rechaza `DELETE` y `TRUNCATE`); un saldo en 0 permanece.

## 9.2 InventoryMovement

**Tabla:** `inventory_movements`  
**Naturaleza:** histórica, privada e inmutable.  
**Servicio propietario:** Inventory Service.

### Descripción

Representa cada cambio individual que ocurre en el inventario y conserva la historia completa del producto, es decir, el kardex.

Registra saldo anterior, cantidad, saldo nuevo, costo y valor, documento de origen, operación y usuario.

No se edita ni elimina y una anulación crea un movimiento inverso.

Inventory Service es el único autorizado para crear movimientos y modificar saldos.

### Atributos

| Atributo               | Tipo            | Regla               | Descripción                                                                 |
| ---------------------- | --------------- | ------------------- | --------------------------------------------------------------------------- |
| `id`                   | `UUID`          | PK, NN              | Identificador.                                                              |
| `operation_id`         | `UUID`          | FK, NN              | Operación de inventario que lo creó (idempotencia por clave del consumidor o del usuario). |
| `company_id`           | `UUID`          | REF, NN             | Empresa.                                                                    |
| `branch_id`            | `UUID`          | REF, NN             | Sucursal.                                                                   |
| `company_product_id`   | `UUID`          | REF, NN             | Producto.                                                                   |
| `movement_type`        | `VARCHAR(40)`   | NN, CK              | Tipo de movimiento.                                                         |
| `quantity`             | `NUMERIC(18,4)` | NN, CK              | Cantidad absoluta en unidad base; mayor que cero.                           |
| `previous_balance`     | `NUMERIC(18,4)` | NN, CK              | Saldo anterior.                                                             |
| `new_balance`          | `NUMERIC(18,4)` | NN, CK              | Saldo nuevo.                                                                |
| `balance_sequence`     | `BIGINT`        | NN, UQ              | Correlativo del movimiento dentro de su saldo, desde 1 y sin huecos.        |
| `unit_cost`            | `NUMERIC(18,4)` | nullable, CK        | Costo unitario: el informado en entradas y ajustes positivos; en salidas, ajustes negativos y reversos, el que resulta de sus consumos (`movement_value / quantity`, 4 decimales; el reverso de una entrada informa el costo de su capa). Nulo solo en movimientos anteriores a la valoración. |
| `origin_type`          | `VARCHAR(30)`   | NN                  | Tipo de origen (`PURCHASE`, `SALE`, `ADJUSTMENT`, `COUNT`).                 |
| `origin_id`            | `UUID`          | NN                  | Documento; en ajustes, el ajuste; en conteos, el conteo.                    |
| `origin_detail_id`     | `UUID`          | NN                  | Línea; en ajustes, el ajuste; en conteos, el detalle del conteo.            |
| `line_index`           | `SMALLINT`      | NN, UQ              | Posición de la línea en la operación.                                       |
| `application_user_id`  | `UUID`          | REF, NN             | Usuario operativo que confirmó o anuló el documento, o que registró el ajuste o el conteo. |
| `correlation_id`       | `UUID`          | NN                  | Flujo distribuido.                                                          |
| `reason`               | `TEXT`          | nullable            | Motivo (obligatorio en reversos y ajustes).                                 |
| `reversed_movement_id` | `UUID`          | FK, nullable, UQ    | Movimiento revertido.                                                      |
| `created_at`           | `TIMESTAMPTZ`   | NN                  | Fecha.                                                                      |
| `created_by`           | `VARCHAR(255)`  | NN                  | `sub` de la cuenta de servicio o del usuario que aplicó la operación (D1).  |
| `updated_at`           | `TIMESTAMPTZ`   | NN, CK              | Igual a `created_at`.                                                       |
| `updated_by`           | `VARCHAR(255)`  | NN, CK              | Igual a `created_by`.                                                       |
| `movement_value`       | `NUMERIC(18,2)` | nullable, CK        | Valor del movimiento; no negativo. En salidas y reversos, Σ `cost_amount` de sus consumos. Nulo solo antes de la valoración. |
| `cost_known`           | `BOOLEAN`       | nullable, CK        | `false` si el movimiento consumió o retiró unidades de apertura sin costo histórico. Nulo solo antes de la valoración. |

### Reglas y restricciones

- Tipos: `PURCHASE_ENTRY`, `SALE_OUTPUT`, `ENTRY_REVERSAL`, `OUTPUT_REVERSAL`, `POSITIVE_ADJUSTMENT` y `NEGATIVE_ADJUSTMENT`.
- La cantidad debe ser mayor que cero; los saldos anterior y nuevo, no negativos; `new_balance = previous_balance + quantity` para entradas, reversos de salida y ajustes positivos, y `- quantity` para salidas, reversos de entrada y ajustes negativos.
- `balance_sequence` es único por empresa, sucursal y producto; se asigna como `version + 1` con la fila del saldo bloqueada y en la misma transacción (no se usa una `SEQUENCE`), de modo que las operaciones confirmadas forman un kardex sin huecos y encadenado (`previous_balance` = `new_balance` del anterior).
- Los movimientos son inmutables: la base rechaza `UPDATE`, `DELETE` y `TRUNCATE`; `updated_at`/`updated_by` son iguales a `created_at`/`created_by` por restricción.
- Una anulación crea un movimiento inverso por cada movimiento de la operación original (`reversed_movement_id`), una sola vez; un reverso no se revierte.
- Todo movimiento nuevo es valorizado: `unit_cost`, `movement_value` y `cost_known` son obligatorios por la restricción `ck_inventory_movements_valued`, creada `NOT VALID` para no revalidar el historial de la Fase A (inmutable).
- El costo de las salidas, los ajustes negativos y los reversos se obtiene de `InventoryCostConsumption`; ninguna operación crea cantidad nueva sin costo conocido, salvo las capas de apertura (§9.6).

> **Reconciliación (2026-10-06):** secciones alineadas con `specs/012-inventory-core` (Inventory Service
> Fase A, BR-12): columnas de auditoría `created_at`/`created_by`/`updated_at`/`updated_by` con el `sub`
> (D1) en ambas tablas e iguales por restricción en los movimientos; `application_user_id` en lugar de
> `created_by_user_id`; `operation_id` obligatorio (FK a la operación de inventario) y `balance_sequence`;
> `origin_detail_id` obligatorio; `version` como contador desde 0; inmutabilidad en la base y saldo
> nunca negativo. Los nombres de restricciones e índices, y la tabla técnica `inventory_operations`,
> están en el `data-model.md` de esa feature. Las columnas de valoración, diferidas entonces, quedaron
> implementadas en la Fase B (BR-13, nota al final de §9.9).

## 9.3 InventoryAdjustment

**Tabla:** `inventory_adjustments`  
**Naturaleza:** transaccional, privada, histórica e inmutable.  
**Servicio propietario:** Inventory Service.

### Descripción

Representa una corrección manual y controlada del inventario cuando la cantidad registrada en SIO no coincide con la cantidad real encontrada en una sucursal.

Se usa por conteo físico, pérdida, daño, producto encontrado o corrección autorizada.

No debe ocultar errores de compras o ventas; esos casos requieren anulación y reverso.

Cada ajuste genera obligatoriamente un movimiento de inventario.

### Atributos

| Atributo              | Tipo            | Regla            | Descripción                                                              |
| --------------------- | --------------- | ---------------- | ------------------------------------------------------------------------ |
| `id`                  | `UUID`          | PK, NN           | Identificador.                                                           |
| `operation_id`        | `UUID`          | FK, NN           | Operación de inventario (`ADJUSTMENT`) que lo aplicó.                    |
| `movement_id`         | `UUID`          | FK, NN, UQ       | Movimiento generado.                                                     |
| `company_id`          | `UUID`          | REF, NN          | Empresa.                                                                 |
| `branch_id`           | `UUID`          | REF, NN          | Sucursal.                                                                |
| `company_product_id`  | `UUID`          | REF, NN          | Producto.                                                                |
| `adjustment_type`     | `VARCHAR(30)`   | NN, CK           | `POSITIVE` o `NEGATIVE`.                                                 |
| `quantity`            | `NUMERIC(18,4)` | NN, CK           | Cantidad; mayor que cero.                                                |
| `reason`              | `TEXT`          | NN, CK           | Justificación; no vacía, sin espacios externos, hasta 2 000 caracteres.  |
| `previous_balance`    | `NUMERIC(18,4)` | NN, CK           | Saldo anterior.                                                          |
| `new_balance`         | `NUMERIC(18,4)` | NN, CK           | Saldo nuevo, coherente con el tipo; no negativo.                         |
| `unit_cost`           | `NUMERIC(18,4)` | NN, CK           | Costo aplicado: FIFO en negativos; informado o de la capa más reciente en positivos. |
| `adjustment_value`    | `NUMERIC(18,2)` | NN, CK           | Valor del ajuste.                                                        |
| `inventory_count_id`  | `UUID`          | FK, nullable     | Conteo que lo generó.                                                    |
| `application_user_id` | `UUID`          | REF, NN          | Usuario operativo que lo registró.                                       |
| `created_at`          | `TIMESTAMPTZ`   | NN, CK           | Creación.                                                                |
| `created_by`          | `VARCHAR(255)`  | NN, CK           | `sub` del usuario (D1).                                                  |
| `updated_at`          | `TIMESTAMPTZ`   | NN, CK           | Igual a `created_at`.                                                    |
| `updated_by`          | `VARCHAR(255)`  | NN, CK           | Igual a `created_by`.                                                    |

### Reglas y restricciones

- El ajuste se aplica al registrarlo (sin estados de aprobación); un ajuste rechazado no se guarda. Es inmutable (la base rechaza `UPDATE`, `DELETE` y `TRUNCATE`) y se corrige con otro ajuste de sentido contrario.
- Solo lo registra un usuario humano con el permiso, membresía `ACTIVE` y asignación `ACTIVE` a la sucursal.
- Un ajuste negativo consume capas FIFO; uno positivo crea una capa con el costo informado o, si no se informa, con el de la capa más reciente; sin capas, o si la más reciente no tiene costo conocido, el costo es obligatorio.

## 9.4 CompanyInventoryPolicy

**Tabla:** `company_inventory_policies`  
**Naturaleza:** configuración privada por empresa.  
**Servicio propietario:** Inventory Service.

### Descripción

Define la política general con la que una empresa administra y valora su inventario.

El método de valoración se configura por empresa para evitar que distintas sucursales produzcan criterios financieros incompatibles.

### Atributos

| Atributo                 | Tipo           | Regla                    | Descripción                                              |
| ------------------------ | -------------- | ------------------------ | -------------------------------------------------------- |
| `id`                     | `UUID`         | PK, NN                   | Identificador.                                           |
| `company_id`             | `UUID`         | REF, NN, UQ              | Empresa propietaria.                                     |
| `inventory_system`       | `VARCHAR(20)`  | NN, CK                   | `PERPETUAL` o `PERIODIC`.                                |
| `valuation_method`       | `VARCHAR(30)`  | NN, CK, DEFAULT `FIFO`   | Solo `FIFO`.                                             |
| `replenishment_strategy` | `VARCHAR(20)`  | NN, CK                   | `STANDARD` o `JIT`.                                      |
| `is_active`              | `BOOLEAN`      | NN, DEFAULT `true`       | Siempre `TRUE`: la política no se desactiva ni se elimina (solo lectura). |
| `version`                | `INTEGER`      | NN, DEFAULT `1`          | Control concurrente.                                     |
| `created_at`             | `TIMESTAMPTZ`  | NN                       | Creación.                                                |
| `created_by`             | `VARCHAR(255)` | NN                       | `sub` del usuario (D1).                                  |
| `updated_at`             | `TIMESTAMPTZ`  | NN                       | Modificación.                                            |
| `updated_by`             | `VARCHAR(255)` | NN                       | `sub` del usuario (D1).                                  |

### Reglas y restricciones

- Una política por empresa; si la empresa no registró la suya se informa la política por defecto `PERPETUAL` + `FIFO` + `STANDARD`.
- `PERIODIC` se guarda sin cambiar el motor perpetuo; `JIT` es una estrategia de reposición y no un método de valoración.
- El cambio de método de valoración no está disponible: la valoración es FIFO para toda empresa y el historial valorizado no se reinterpreta.

## 9.5 InventoryPolicy

**Tabla:** `inventory_policies`  
**Naturaleza:** configuración privada por empresa, sucursal y producto.  
**Servicio propietario:** Inventory Service.

### Descripción

Define los parámetros de reposición y control de inventario de un producto en una sucursal específica.

Reemplaza el concepto de `minimum_stock` general en `CompanyProduct`, porque los niveles necesarios pueden variar entre bodegas y puntos de venta.

### Atributos

| Atributo                  | Tipo            | Regla                    | Descripción                                        |
| ------------------------- | --------------- | ------------------------ | -------------------------------------------------- |
| `id`                      | `UUID`          | PK, NN                   | Identificador.                                     |
| `company_id`              | `UUID`          | REF, NN                  | Empresa.                                           |
| `branch_id`               | `UUID`          | REF, NN                  | Sucursal.                                          |
| `company_product_id`      | `UUID`          | REF, NN                  | Producto empresarial.                              |
| `minimum_stock`           | `NUMERIC(18,4)` | NN, DEFAULT `0`, CK      | Nivel mínimo operativo configurado; no negativo.   |
| `target_stock`            | `NUMERIC(18,4)` | nullable, CK             | Nivel objetivo; mayor o igual que el mínimo.       |
| `service_level`           | `NUMERIC(7,4)`  | nullable, CK             | Nivel de servicio; mayor que 0 y menor que 1.      |
| `safety_stock_method`     | `VARCHAR(20)`   | NN, CK                   | `BASIC` o `STATISTICAL`.                           |
| `calculation_window_days` | `INTEGER`       | NN, DEFAULT `90`, CK     | Ventana histórica para cálculos; de 1 a 3 650 días. |
| `replenishment_mode`      | `VARCHAR(20)`   | NN, CK                   | `MANUAL` o `AUTO_DRAFT`.                           |
| `auto_purchase_enabled`   | `BOOLEAN`       | NN, DEFAULT `false`      | Solo configuración: no genera compras en esta fase. |
| `is_active`               | `BOOLEAN`       | NN, DEFAULT `true`       | Vigencia.                                          |
| `version`                 | `INTEGER`       | NN, DEFAULT `1`          | Control concurrente.                               |
| `created_at`              | `TIMESTAMPTZ`   | NN                       | Creación.                                          |
| `created_by`              | `VARCHAR(255)`  | NN                       | `sub` del usuario (D1).                            |
| `updated_at`              | `TIMESTAMPTZ`   | NN                       | Modificación.                                      |
| `updated_by`              | `VARCHAR(255)`  | NN                       | `sub` del usuario (D1).                            |

### Reglas y restricciones

- Solo existe una política activa por empresa, sucursal y producto (índice único parcial).
- Se inactiva con control de versión, sin eliminarse.
- `AUTO_DRAFT` nunca confirma una compra automáticamente; la política es solo configuración y no genera compras ni métricas en esta fase.
- Los valores calculados de stock de seguridad y ROP no se almacenan como configuración fija en esta entidad.

## 9.6 InventoryCostLayer

**Tabla:** `inventory_cost_layers`  
**Naturaleza:** financiera, privada e histórica.  
**Servicio propietario:** Inventory Service.

### Descripción

Representa una capa de costo utilizada por el método FIFO.

Cada entrada y cada ajuste positivo crean una capa con cantidad recibida, cantidad restante y costo unitario; los saldos anteriores a la valoración recibieron una capa de apertura.

Las salidas y los ajustes negativos consumen primero las capas abiertas más antiguas de la misma empresa, sucursal y producto.

### Atributos

| Atributo                    | Tipo            | Regla                    | Descripción                                                         |
| --------------------------- | --------------- | ------------------------ | ------------------------------------------------------------------- |
| `id`                        | `UUID`          | PK, NN                   | Identificador.                                                      |
| `company_id`                | `UUID`          | REF, NN                  | Empresa.                                                            |
| `branch_id`                 | `UUID`          | REF, NN                  | Sucursal.                                                           |
| `company_product_id`        | `UUID`          | REF, NN                  | Producto.                                                           |
| `layer_kind`                | `VARCHAR(20)`   | NN, CK                   | `ENTRY`, `ADJUSTMENT` u `OPENING`.                                  |
| `origin_movement_id`        | `UUID`          | FK, nullable, UQ, CK     | Movimiento que creó la capa; nulo solo en `OPENING`.                |
| `origin_purchase_id`        | `UUID`          | REF, nullable            | Documento de la entrada (`origin_id` del movimiento).               |
| `origin_purchase_detail_id` | `UUID`          | REF, nullable            | Línea de la entrada (`origin_detail_id` del movimiento).            |
| `original_quantity`         | `NUMERIC(18,4)` | NN, CK                   | Cantidad original; mayor que cero.                                  |
| `remaining_quantity`        | `NUMERIC(18,4)` | NN, CK                   | Cantidad aún no consumida; entre cero y la original.                |
| `unit_cost`                 | `NUMERIC(18,4)` | NN, CK                   | Costo unitario de la capa; no negativo.                             |
| `cost_known`                | `BOOLEAN`       | NN, CK                   | `false` solo en aperturas sin costo histórico (con `unit_cost = 0`). |
| `currency_code`             | `CHAR(3)`       | nullable, CK             | `default_currency` de la empresa al crear la capa; nulo solo en las aperturas creadas por la migración. |
| `received_at`               | `TIMESTAMPTZ`   | NN                       | Momento de disponibilidad de la capa (orden FIFO con `id`).         |
| `status`                    | `VARCHAR(20)`   | NN, CK                   | `OPEN` si queda cantidad; `CLOSED` si llegó a cero.                 |
| `created_at`                | `TIMESTAMPTZ`   | NN                       | Creación.                                                           |
| `created_by`                | `VARCHAR(255)`  | NN                       | `sub` de quien aplicó el movimiento que la creó (D1).               |
| `updated_at`                | `TIMESTAMPTZ`   | NN                       | Actualización de cantidad restante.                                 |
| `updated_by`                | `VARCHAR(255)`  | NN                       | `sub` del último movimiento que la modificó.                        |

### Reglas y restricciones

- `remaining_quantity` debe estar entre cero y `original_quantity`; `status = OPEN` si `remaining_quantity > 0` y `CLOSED` si es 0.
- Orden FIFO por `received_at` e `id`; las capas solo cambian con su saldo bloqueado, en la misma transacción del movimiento, y no se eliminan (la base rechaza `DELETE` y `TRUNCATE`). La selección FIFO es atómica con el movimiento: ninguna capa se consume dos veces.
- `cost_known = false` solo en aperturas, con `unit_cost = 0`; el costo desconocido se propaga a consumos, movimientos y saldos y nunca se deduce de `unit_cost = 0`. Ninguna otra capa se crea sin costo conocido.
- Una sola apertura por saldo (índice único parcial), creada por la migración para los saldos anteriores a la valoración con el costo de su última entrada con costo no revertida, o "sin costo".

## 9.7 InventoryCostConsumption

**Tabla:** `inventory_cost_consumptions`  
**Naturaleza:** histórica, financiera e inmutable.  
**Servicio propietario:** Inventory Service.

### Descripción

Registra qué capas de costo consumió, restituyó o retiró un movimiento de inventario.

Permite reconstruir el costo de ventas exacto y conservar la trazabilidad FIFO.

### Atributos

| Atributo                  | Tipo            | Regla                | Descripción                                               |
| ------------------------- | --------------- | -------------------- | --------------------------------------------------------- |
| `id`                      | `UUID`          | PK, NN               | Identificador.                                            |
| `movement_id`             | `UUID`          | FK, NN               | Movimiento que consume, restituye o retira.               |
| `cost_layer_id`           | `UUID`          | FK, NN               | Capa afectada.                                            |
| `consumption_type`        | `VARCHAR(20)`   | NN, CK               | `CONSUME`, `RESTORE` o `ENTRY_REVERSAL`.                  |
| `restores_consumption_id` | `UUID`          | FK, nullable, UQ, CK | Consumo original que restituye; obligatorio en `RESTORE`. |
| `quantity`                | `NUMERIC(18,4)` | NN, CK               | Cantidad; mayor que cero.                                 |
| `unit_cost`               | `NUMERIC(18,4)` | NN                   | Costo histórico de la capa.                               |
| `cost_known`              | `BOOLEAN`       | NN                   | Copia de `cost_known` de la capa.                         |
| `cost_amount`             | `NUMERIC(18,2)` | NN                   | `round(quantity × unit_cost, 2)` con `ROUND_HALF_UP`.     |
| `created_at`              | `TIMESTAMPTZ`   | NN                   | Creación.                                                 |
| `created_by`              | `VARCHAR(255)`  | NN                   | `sub` de quien aplicó el movimiento (D1).                 |

### Reglas y restricciones

- Los consumos son inmutables (la base rechaza `UPDATE`, `DELETE` y `TRUNCATE`).
- La suma de los consumos de un movimiento explica su valor (`movement_value`).
- El reverso de una salida crea un `RESTORE` por cada consumo original, en la misma capa y con el mismo costo, sin modificar consumos históricos; una salida sin consumos (anterior a la valoración) no se revierte.
- El reverso de una entrada crea un `ENTRY_REVERSAL` y exige su capa completa; una entrada anterior a la valoración se retira de la capa de apertura si conserva cantidad suficiente.

## 9.8 InventoryCount

**Tabla:** `inventory_counts`  
**Naturaleza:** transaccional, privada e histórica.  
**Servicio propietario:** Inventory Service.

### Descripción

Representa un conteo físico de inventario en una sucursal.

Permite soportar procesos de conteo sin utilizar `InventoryAdjustment` como sustituto del proceso completo.

### Atributos

| Atributo               | Tipo           | Regla             | Descripción                                                     |
| ---------------------- | -------------- | ----------------- | --------------------------------------------------------------- |
| `id`                   | `UUID`         | PK, NN            | Identificador.                                                  |
| `company_id`           | `UUID`         | REF, NN           | Empresa.                                                        |
| `branch_id`            | `UUID`         | REF, NN           | Sucursal.                                                       |
| `status`               | `VARCHAR(20)`  | NN, CK            | `DRAFT`, `IN_PROGRESS`, `COMPLETED` o `CANCELLED`.              |
| `started_by_user_id`   | `UUID`         | REF, NN           | Usuario operativo responsable (quien lo crea).                  |
| `started_at`           | `TIMESTAMPTZ`  | nullable, CK      | Inicio real.                                                    |
| `completed_by_user_id` | `UUID`         | REF, nullable, CK | Usuario que completa.                                           |
| `completed_at`         | `TIMESTAMPTZ`  | nullable, CK      | Finalización.                                                   |
| `cancelled_by_user_id` | `UUID`         | REF, nullable, CK | Usuario que cancela.                                            |
| `cancelled_at`         | `TIMESTAMPTZ`  | nullable, CK      | Cancelación.                                                    |
| `cancel_reason`        | `TEXT`         | nullable, CK      | Motivo de la cancelación.                                       |
| `operation_id`         | `UUID`         | FK, nullable, CK  | Operación de ajustes al completar; nula si no hubo diferencias. |
| `observations`         | `TEXT`         | nullable          | Observaciones generales.                                        |
| `version`              | `INTEGER`      | NN, DEFAULT `1`   | Control concurrente.                                            |
| `created_at`           | `TIMESTAMPTZ`  | NN                | Creación.                                                       |
| `created_by`           | `VARCHAR(255)` | NN                | `sub` del usuario (D1).                                         |
| `updated_at`           | `TIMESTAMPTZ`  | NN                | Modificación.                                                   |
| `updated_by`           | `VARCHAR(255)` | NN                | `sub` del usuario (D1).                                         |

### Reglas y restricciones

- Transiciones `DRAFT → IN_PROGRESS → COMPLETED` y `DRAFT | IN_PROGRESS → CANCELLED`, con control de versión; los campos de cada estado son coherentes por restricción.
- Un solo conteo `IN_PROGRESS` por sucursal (índice único parcial).
- Completar aplica todas las diferencias registradas como **una** operación de ajustes (origen `COUNT`) sobre el saldo vigente, todo o nada.
- Solo lo operan usuarios humanos con el permiso, membresía `ACTIVE` y asignación `ACTIVE` a la sucursal.

## 9.9 InventoryCountDetail

**Tabla:** `inventory_count_details`  
**Naturaleza:** transaccional, privada e histórica.  
**Servicio propietario:** Inventory Service.

### Descripción

Conserva el resultado del conteo físico por producto y la diferencia contra el saldo de sistema observado para el proceso.

### Atributos

| Atributo                   | Tipo            | Regla         | Descripción                                                  |
| -------------------------- | --------------- | ------------- | ------------------------------------------------------------ |
| `id`                       | `UUID`          | PK, NN        | Identificador.                                               |
| `inventory_count_id`       | `UUID`          | FK, NN, UQ    | Conteo físico.                                               |
| `company_product_id`       | `UUID`          | REF, NN, UQ   | Producto.                                                    |
| `system_quantity_snapshot` | `NUMERIC(18,4)` | NN, CK        | Saldo de sistema al registrar el producto.                   |
| `counted_quantity`         | `NUMERIC(18,4)` | NN, CK        | Cantidad física encontrada.                                  |
| `difference_quantity`      | `NUMERIC(18,4)` | NN, CK        | Diferencia física contra sistema.                            |
| `unit_cost`                | `NUMERIC(18,4)` | nullable, CK  | Costo de un sobrante sin costo conocido.                     |
| `inventory_adjustment_id`  | `UUID`          | FK, nullable  | Ajuste generado cuando corresponde.                          |
| `counted_by_user_id`       | `UUID`          | REF, NN       | Usuario que registra el conteo.                              |
| `counted_at`               | `TIMESTAMPTZ`   | NN            | Momento del conteo.                                          |
| `created_at`               | `TIMESTAMPTZ`   | NN            | Creación.                                                    |
| `created_by`               | `VARCHAR(255)`  | NN            | `sub` del usuario (D1).                                      |
| `updated_at`               | `TIMESTAMPTZ`   | NN            | Último registro.                                             |
| `updated_by`               | `VARCHAR(255)`  | NN            | `sub` del usuario (D1).                                      |

### Reglas y restricciones

- Un producto aparece como máximo una vez dentro de un conteo; un nuevo registro reemplaza el anterior y vuelve a tomar el saldo del sistema.
- `difference_quantity = counted_quantity - system_quantity_snapshot`.
- Un conteo admite hasta 1 000 productos.
- Los detalles solo cambian mientras el conteo está `IN_PROGRESS`: la base rechaza cambios de detalles de conteos finalizados.

> **Reconciliación (2026-10-06):** sección 9 alineada con `specs/013-inventory-complementary`
> (Inventory Service Fase B, BR-13): valoración FIFO como único método; columnas de valoración en saldos
> (`average_unit_cost`, `inventory_value`, `has_unknown_cost`) y movimientos (`unit_cost` en todo
> movimiento valorizado, `movement_value`, `cost_known`, tipos de ajuste); ajustes aplicados al
> registrarlos e inmutables, sin estado `REJECTED`, con operación, costo y valor; usuarios como
> `application_user_id`; columnas de auditoría `created_*`/`updated_*` con el `sub` (D1); política única
> de la empresa solo `FIFO` y siempre activa; capas `ENTRY`, `ADJUSTMENT` y `OPENING` con `cost_known` y
> propagación del costo desconocido; consumos `CONSUME`, `RESTORE` y `ENTRY_REVERSAL`; conteos con
> cancelación, operación y versión; `currency_code` nulo únicamente en las capas `OPENING` históricas. El
> promedio ponderado (`WEIGHTED_AVERAGE`) no está implementado y queda fuera del MVP. Los nombres de
> restricciones, índices y triggers están en el `data-model.md` de esa feature.

# 10. Finance DB

`Finance Service` administra la liquidación financiera de compras y ventas.

Es la fuente oficial de cuentas por pagar, cuentas por cobrar, pagos, recaudos, saldos pendientes y vencimientos.

La condición comercial se origina en `Commercial Relationship Service` y queda como snapshot en Purchase o Sale.

El saldo de cartera nunca se almacena en `CompanySupplier` ni `CompanyCustomer`.

Para mantener un modelo uniforme, una compra o venta confirmada puede generar su obligación financiera incluso cuando sea `CASH`, en ese caso la obligación debe quedar liquidada mediante el pago o recaudo correspondiente y normalmente tendrá vencimiento inmediato.

## Cuentas de pago a proveedor

## 10.1 AccountPayable

**Tabla:** `accounts_payable`  
**Naturaleza:** financiera, privada y transaccional.  
**Servicio propietario:** Finance Service.

### Descripción

Representa una obligación de pago de la empresa frente a un proveedor originada por una compra confirmada.

Permite consultar la cartera del proveedor sin modificar `CompanySupplier`.

### Atributos

| Atributo                          | Tipo            | Regla           | Descripción                                                |
| --------------------------------- | --------------- | --------------- | ---------------------------------------------------------- |
| `id`                              | `UUID`          | PK, NN          | Identificador.                                             |
| `company_id`                      | `UUID`          | REF, NN         | Empresa obligada.                                          |
| `branch_id`                       | `UUID`          | REF, nullable   | Sucursal de origen.                                        |
| `company_supplier_id`             | `UUID`          | REF, NN         | Proveedor.                                                 |
| `purchase_id`                     | `UUID`          | REF, NN, UQ     | Compra origen.                                             |
| `currency_code`                   | `CHAR(3)`       | NN              | Moneda.                                                    |
| `payment_condition_code_snapshot` | `VARCHAR(30)`   | NN              | `CASH`, `CREDIT` o `FINANCING`.                            |
| `original_amount`                 | `NUMERIC(18,2)` | NN              | Valor original.                                            |
| `paid_amount`                     | `NUMERIC(18,2)` | NN, DEFAULT `0` | Valor aplicado en pagos.                                   |
| `outstanding_amount`              | `NUMERIC(18,2)` | NN              | Saldo pendiente.                                           |
| `issued_at`                       | `TIMESTAMPTZ`   | NN              | Momento de creación de la obligación.                      |
| `due_date`                        | `DATE`          | NN              | Fecha de vencimiento.                                      |
| `status`                          | `VARCHAR(30)`   | NN, CK          | `OPEN`, `PARTIALLY_PAID`, `PAID`, `OVERDUE` o `CANCELLED`. |
| `version`                         | `INTEGER`       | NN, DEFAULT `1` | Control concurrente.                                       |
| `created_at`                      | `TIMESTAMPTZ`   | NN              | Creación.                                                  |
| `updated_at`                      | `TIMESTAMPTZ`   | NN              | Modificación.                                              |

### Reglas y restricciones

- Solo existe una cuenta por pagar fuente por `purchase_id` en el alcance inicial.
- `original_amount`, `paid_amount` y `outstanding_amount` no pueden ser negativos.
- Debe cumplirse `paid_amount + outstanding_amount = original_amount`, salvo ajustes financieros explícitos futuros.
- Finance Service es el único servicio autorizado para actualizar saldos.
- Una obligación vencida con saldo pendiente puede clasificarse como `OVERDUE` sin alterar la compra original.

## 10.2 SupplierPayment

**Tabla:** `supplier_payments`  
**Naturaleza:** financiera, privada e histórica.  
**Servicio propietario:** Finance Service.

### Descripción

Representa una salida de dinero realizada por la empresa a un proveedor.

Un pago puede aplicarse a una o varias cuentas por pagar mediante `SupplierPaymentAllocation`.

### Atributos

| Atributo              | Tipo            | Regla    | Descripción                                             |
| --------------------- | --------------- | -------- | ------------------------------------------------------- |
| `id`                  | `UUID`          | PK, NN   | Identificador.                                          |
| `company_id`          | `UUID`          | REF, NN  | Empresa pagadora.                                       |
| `company_supplier_id` | `UUID`          | REF, NN  | Proveedor receptor.                                     |
| `payment_method_id`   | `UUID`          | REF, NN  | Medio de pago global.                                   |
| `currency_code`       | `CHAR(3)`       | NN       | Moneda.                                                 |
| `amount`              | `NUMERIC(18,2)` | NN       | Valor pagado.                                           |
| `external_reference`  | `VARCHAR(150)`  | nullable | Comprobante, referencia bancaria u otro identificador.  |
| `paid_at`             | `TIMESTAMPTZ`   | NN       | Momento del pago.                                       |
| `recorded_by_user_id` | `UUID`          | REF, NN  | Usuario que registró.                                   |
| `status`              | `VARCHAR(20)`   | NN, CK   | `RECORDED` o `VOIDED`.                                  |
| `idempotency_key`     | `VARCHAR(150)`  | NN, UQ   | Evita registrar dos veces el mismo pago por reintentos. |
| `created_at`          | `TIMESTAMPTZ`   | NN       | Creación.                                               |
| `updated_at`          | `TIMESTAMPTZ`   | NN       | Modificación.                                           |

### Reglas y restricciones

- `amount` debe ser mayor que cero.
- El medio de pago debe estar activo al registrar el pago.
- Un pago anulado no se elimina; sus aplicaciones deben revertirse de forma trazable.

## 10.3 SupplierPaymentAllocation

**Tabla:** `supplier_payment_allocations`  
**Naturaleza:** financiera y transaccional.  
**Servicio propietario:** Finance Service.

### Descripción

Distribuye un pago a proveedor entre una o varias cuentas por pagar.

### Atributos

| Atributo              | Tipo            | Regla  | Descripción            |
| --------------------- | --------------- | ------ | ---------------------- |
| `id`                  | `UUID`          | PK, NN | Identificador.         |
| `supplier_payment_id` | `UUID`          | FK, NN | Pago.                  |
| `account_payable_id`  | `UUID`          | FK, NN | Obligación aplicada.   |
| `allocated_amount`    | `NUMERIC(18,2)` | NN     | Valor aplicado.        |
| `allocated_at`        | `TIMESTAMPTZ`   | NN     | Momento de aplicación. |
| `created_at`          | `TIMESTAMPTZ`   | NN     | Creación.              |

### Reglas y restricciones

- `allocated_amount` debe ser mayor que cero.
- La suma de aplicaciones activas no puede superar el valor del pago.
- Una aplicación no puede superar el saldo pendiente de la cuenta por pagar.
- Pago, obligación, proveedor, empresa y moneda deben ser compatibles.

## Cuenta por cobrar de la empresa a un cliente

## 10.4 AccountReceivable

**Tabla:** `accounts_receivable`  
**Naturaleza:** financiera, privada y transaccional.  
**Servicio propietario:** Finance Service.

### Descripción

Representa el valor que un cliente debe a la empresa como resultado de una venta confirmada.

Permite consultar la cartera real del cliente sin almacenar el saldo dentro de `CompanyCustomer`.

### Atributos

| Atributo                          | Tipo            | Regla           | Descripción                                                |
| --------------------------------- | --------------- | --------------- | ---------------------------------------------------------- |
| `id`                              | `UUID`          | PK, NN          | Identificador.                                             |
| `company_id`                      | `UUID`          | REF, NN         | Empresa acreedora.                                         |
| `branch_id`                       | `UUID`          | REF, nullable   | Sucursal origen.                                           |
| `company_customer_id`             | `UUID`          | REF, NN         | Cliente.                                                   |
| `sale_id`                         | `UUID`          | REF, NN, UQ     | Venta origen.                                              |
| `currency_code`                   | `CHAR(3)`       | NN              | Moneda.                                                    |
| `payment_condition_code_snapshot` | `VARCHAR(30)`   | NN              | `CASH`, `CREDIT` o `FINANCING`.                            |
| `original_amount`                 | `NUMERIC(18,2)` | NN              | Valor original.                                            |
| `received_amount`                 | `NUMERIC(18,2)` | NN, DEFAULT `0` | Valor recaudado y aplicado.                                |
| `outstanding_amount`              | `NUMERIC(18,2)` | NN              | Saldo pendiente.                                           |
| `issued_at`                       | `TIMESTAMPTZ`   | NN              | Creación de la cuenta.                                     |
| `due_date`                        | `DATE`          | NN              | Fecha de vencimiento.                                      |
| `status`                          | `VARCHAR(30)`   | NN, CK          | `OPEN`, `PARTIALLY_PAID`, `PAID`, `OVERDUE` o `CANCELLED`. |
| `version`                         | `INTEGER`       | NN, DEFAULT `1` | Control concurrente.                                       |
| `created_at`                      | `TIMESTAMPTZ`   | NN              | Creación.                                                  |
| `updated_at`                      | `TIMESTAMPTZ`   | NN              | Modificación.                                              |

### Reglas y restricciones

- Solo existe una cuenta por cobrar fuente por `sale_id` en el alcance inicial.
- Debe cumplirse `received_amount + outstanding_amount = original_amount`, salvo ajustes financieros explícitos futuros.
- Finance Service es el único servicio autorizado para actualizar saldos.
- El estado `OVERDUE` depende de vencimiento y saldo pendiente; no modifica la venta original.

## 10.5 CustomerPayment

**Tabla:** `customer_payments`  
**Naturaleza:** financiera, privada e histórica.  
**Servicio propietario:** Finance Service.

### Descripción

Representa un recaudo recibido de un cliente.

Puede utilizar cualquier medio de pago activo y puede aplicarse a una o varias cuentas por cobrar mediante `CustomerPaymentAllocation`.

### Atributos

| Atributo              | Tipo            | Regla    | Descripción                |
| --------------------- | --------------- | -------- | -------------------------- |
| `id`                  | `UUID`          | PK, NN   | Identificador.             |
| `company_id`          | `UUID`          | REF, NN  | Empresa receptora.         |
| `company_customer_id` | `UUID`          | REF, NN  | Cliente pagador.           |
| `payment_method_id`   | `UUID`          | REF, NN  | Medio de pago global.      |
| `currency_code`       | `CHAR(3)`       | NN       | Moneda.                    |
| `amount`              | `NUMERIC(18,2)` | NN       | Valor recibido.            |
| `external_reference`  | `VARCHAR(150)`  | nullable | Referencia de transacción. |
| `received_at`         | `TIMESTAMPTZ`   | NN       | Momento del recaudo.       |
| `recorded_by_user_id` | `UUID`          | REF, NN  | Usuario que registró.      |
| `status`              | `VARCHAR(20)`   | NN, CK   | `RECORDED` o `VOIDED`.     |
| `idempotency_key`     | `VARCHAR(150)`  | NN, UQ   | Idempotencia.              |
| `created_at`          | `TIMESTAMPTZ`   | NN       | Creación.                  |
| `updated_at`          | `TIMESTAMPTZ`   | NN       | Modificación.              |

### Reglas y restricciones

- `amount` debe ser mayor que cero.
- El medio de pago debe estar activo.
- Un recaudo anulado no se elimina; sus aplicaciones se revierten de forma trazable.

## 10.6 CustomerPaymentAllocation

**Tabla:** `customer_payment_allocations`  
**Naturaleza:** financiera y transaccional.  
**Servicio propietario:** Finance Service.

### Descripción

Distribuye un recaudo entre una o varias cuentas por cobrar.

### Atributos

| Atributo                | Tipo            | Regla  | Descripción                 |
| ----------------------- | --------------- | ------ | --------------------------- |
| `id`                    | `UUID`          | PK, NN | Identificador.              |
| `customer_payment_id`   | `UUID`          | FK, NN | Recaudo.                    |
| `account_receivable_id` | `UUID`          | FK, NN | Cuenta por cobrar aplicada. |
| `allocated_amount`      | `NUMERIC(18,2)` | NN     | Valor aplicado.             |
| `allocated_at`          | `TIMESTAMPTZ`   | NN     | Momento de aplicación.      |
| `created_at`            | `TIMESTAMPTZ`   | NN     | Creación.                   |

### Reglas y restricciones

- `allocated_amount` debe ser mayor que cero.
- La suma de aplicaciones activas no puede superar el valor recibido.
- Una aplicación no puede superar el saldo pendiente de la cuenta por cobrar.
- Recaudo, cuenta, cliente, empresa y moneda deben ser compatibles.

# 11. Audit DB

## 11.1 AuditEvent

**Tabla:** `audit_events`  
**Naturaleza:** privada, histórica e inmutable.  
**Servicio propietario:** Audit Service.

### Descripción

Representa la evidencia histórica de una acción importante realizada dentro de SIO.

No es un log técnico genérico.

Permite conocer actor, entidad, empresa, sucursal, resultado, solicitud y flujo distribuido.

No puede modificarse mediante endpoints operativos ni mediante sentencias directas sobre la base.

### Atributos

| Atributo              | Tipo           | Regla                    | Descripción                                                        |
| --------------------- | -------------- | ------------------------ | ------------------------------------------------------------------ |
| `id`                  | `UUID`         | PK, NN                   | Identificador.                                                     |
| `event_id`            | `UUID`         | NN, UQ                   | Evento recibido; clave de idempotencia generada por el emisor.     |
| `company_id`          | `UUID`         | REF, nullable            | Empresa. Nulo = evento de plataforma.                              |
| `branch_id`           | `UUID`         | REF, nullable, CK        | Sucursal; exige `company_id`.                                      |
| `application_user_id` | `UUID`         | REF, nullable            | Usuario operativo.                                                 |
| `keycloak_user_id`    | `UUID`         | nullable                 | Actor en Keycloak.                                                 |
| `username_snapshot`   | `VARCHAR(160)` | nullable, CK             | Nombre histórico.                                                  |
| `action`              | `VARCHAR(50)`  | NN, CK                   | Acción.                                                            |
| `entity_type`         | `VARCHAR(60)`  | NN, CK                   | Tipo de entidad.                                                   |
| `entity_id`           | `UUID`         | nullable                 | Entidad afectada.                                                  |
| `previous_values`     | `JSONB`        | nullable, CK             | Valores anteriores (objeto JSON), ya redactados.                   |
| `new_values`          | `JSONB`        | nullable, CK             | Valores nuevos (objeto JSON), ya redactados.                       |
| `redacted_paths`      | `TEXT[]`       | NN, default `'{}'`       | Rutas de los valores ocultados por la política de redacción.       |
| `result`              | `VARCHAR(20)`  | NN, CK                   | `SUCCESS` o `FAILURE`.                                             |
| `reason`              | `TEXT`         | nullable, CK             | Motivo.                                                            |
| `request_id`          | `UUID`         | nullable                 | Solicitud HTTP.                                                    |
| `correlation_id`      | `UUID`         | nullable                 | Flujo.                                                             |
| `source_service`      | `VARCHAR(80)`  | NN, CK                   | Servicio emisor (`client_id` del token técnico autenticado).       |
| `occurred_at`         | `TIMESTAMPTZ`  | NN                       | Momento de la acción.                                              |
| `content_hash`        | `CHAR(64)`     | NN, CK                   | SHA-256 de la forma canónica del evento y del emisor (idempotencia; no se expone por API). |
| `created_at`          | `TIMESTAMPTZ`  | NN, default `now()`      | Persistencia; la API lo expone como `recorded_at`.                 |
| `created_by`          | `VARCHAR(255)` | NN                       | `sub` de la identidad técnica que registró el evento (D1).         |
| `updated_at`          | `TIMESTAMPTZ`  | NN, default `now()`, CK  | Igual a `created_at`.                                              |
| `updated_by`          | `VARCHAR(255)` | NN, CK                   | Igual a `created_by`.                                              |

### Reglas y restricciones

- La entidad es inmutable: los triggers `tr_audit_events_no_update`, `tr_audit_events_no_delete` y
  `tr_audit_events_no_truncate` (función `audit_events_reject_change()`) rechazan `UPDATE`, `DELETE` y
  `TRUNCATE` también en sesiones manuales. No existen rutas de modificación ni eliminación.
- `updated_at = created_at` y `updated_by = created_by` (`ck_audit_events_audit_unchanged`): las
  columnas de auditoría existen por el estándar, pero nunca divergen.
- `action` cumple `^[A-Z][A-Z0-9_]{0,49}$` y `entity_type` cumple `^[A-Z][A-Za-z0-9]{0,59}$`.
- `branch_id` solo puede informarse con `company_id` (`ck_audit_events_branch_requires_company`).
- `previous_values` y `new_values`, cuando existen, son objetos JSON.
- `username_snapshot` y `reason` (máximo 2000 caracteres) no pueden estar en blanco ni tener
  espacios al inicio o al final; `source_service` no puede estar en blanco.
- `content_hash` es hexadecimal en minúsculas de 64 caracteres. Un `event_id` repetido con el mismo
  contenido canónico y el mismo emisor devuelve el registro existente; con contenido o emisor distinto
  es un conflicto.
- Redacción obligatoria: los valores cuyas claves pertenecen a la política v1 de `libs/sio-audit`
  (`password`, `passwd`, `secret`, `clientsecret`, `token`, `accesstoken`, `refreshtoken`, `idtoken`,
  `authorization`, `apikey`, `credential`, `credentials`, `privatekey`; coincidencia exacta de la
  clave sin distinguir mayúsculas, `-` ni `_`) se reemplazan por `"***"` y su ruta se agrega a `redacted_paths`. El emisor redacta antes
  de persistir en su outbox y Audit vuelve a aplicar la política antes de persistir (defensa en
  profundidad).
- `source_service` y `created_by` se derivan del token técnico autenticado; el emisor no puede
  informarlos.

> **Reconciliación (2026-10-05):** sección alineada con `specs/011-audit-core` (Audit Service núcleo,
> BR-11): columnas de auditoría `created_at`/`created_by`/`updated_at`/`updated_by` con el `sub` (D1) e
> iguales por restricción, `recorded_at` como nombre de API de `created_at`; columnas nuevas
> `redacted_paths` y `content_hash`; formatos de `action` y `entity_type`; inmutabilidad garantizada en
> la base; redacción obligatoria en lugar de la regla genérica sobre secretos. `keycloak_user_id` se
> mantiene `UUID`. Los nombres de restricciones e índices están en el `data-model.md` de esa feature.

# 12. Reporting DB (Seccion solo de ilustracion, se debe definir segun requerimientos)

Las entidades de `Reporting Service` son proyecciones de lectura.

No son fuentes oficiales y pueden reconstruirse desde eventos.

Las métricas se calculan a partir de hechos operacionales confirmados, conservan el periodo y momento de cálculo para permitir comparación histórica.

## 12.1 SupplierPerformanceMetric

**Tabla:** `supplier_performance_metrics`

### Descripción

Proyección periódica del desempeño observado de un proveedor, de forma general o para un producto específico.

### Atributos

| Atributo                  | Tipo            | Regla    | Descripción                                                  |
| ------------------------- | --------------- | -------- | ------------------------------------------------------------ |
| `id`                      | `UUID`          | PK, NN   | Identificador de la proyección.                              |
| `company_id`              | `UUID`          | NN       | Empresa.                                                     |
| `company_supplier_id`     | `UUID`          | NN       | Proveedor privado.                                           |
| `supplier_product_id`     | `UUID`          | nullable | Relación proveedor-producto cuando la métrica es específica. |
| `period_start`            | `DATE`          | NN       | Inicio del periodo.                                          |
| `period_end`              | `DATE`          | NN       | Fin del periodo.                                             |
| `purchase_count`          | `INTEGER`       | NN       | Compras evaluadas.                                           |
| `minimum_lead_time_hours` | `NUMERIC(12,2)` | nullable | Lead time mínimo observado.                                  |
| `average_lead_time_hours` | `NUMERIC(12,2)` | nullable | Lead time promedio observado.                                |
| `maximum_lead_time_hours` | `NUMERIC(12,2)` | nullable | Lead time máximo observado.                                  |
| `lead_time_stddev_hours`  | `NUMERIC(12,2)` | nullable | Desviación estándar.                                         |
| `on_time_delivery_rate`   | `NUMERIC(7,4)`  | nullable | Nivel de cumplimiento calculado.                             |
| `average_rating`          | `NUMERIC(7,4)`  | nullable | Calificación histórica agregada cuando exista.               |
| `calculated_at`           | `TIMESTAMPTZ`   | NN       | Momento de cálculo.                                          |

### Reglas

- El nivel de cumplimiento se deriva de entregas evaluadas y no se captura como un porcentaje maestro editable.
- Para medir cumplimiento se compara el hito real de llegada/recepción definido por la política con `Purchase.promised_delivery_at` conservado para la compra.
- `average_rating` se deriva de `SupplierEvaluation`.
- Las métricas sin suficiente muestra pueden permanecer nulas y deben exponer el número de observaciones.

## 12.2 CustomerMetric

**Tabla:** `customer_metrics`

### Descripción

Proyección periódica del comportamiento comercial de un cliente dentro de una empresa.

### Atributos

| Atributo                         | Tipo            | Regla    | Descripción                                            |
| -------------------------------- | --------------- | -------- | ------------------------------------------------------ |
| `id`                             | `UUID`          | PK, NN   | Identificador.                                         |
| `company_id`                     | `UUID`          | NN       | Empresa.                                               |
| `company_customer_id`            | `UUID`          | NN       | Cliente privado.                                       |
| `period_start`                   | `DATE`          | NN       | Inicio del periodo.                                    |
| `period_end`                     | `DATE`          | NN       | Fin del periodo.                                       |
| `purchase_count`                 | `INTEGER`       | NN       | Número de compras/ventas realizadas por el cliente.    |
| `average_days_between_purchases` | `NUMERIC(12,2)` | nullable | Frecuencia promedio expresada como días entre compras. |
| `average_ticket`                 | `NUMERIC(18,2)` | nullable | Ticket promedio.                                       |
| `net_sales`                      | `NUMERIC(18,2)` | NN       | Ventas netas del periodo.                              |
| `gross_profit`                   | `NUMERIC(18,2)` | nullable | Margen bruto monetario generado.                       |
| `profitability_percentage`       | `NUMERIC(7,4)`  | nullable | Rentabilidad calculada bajo la definición vigente.     |
| `last_purchase_at`               | `TIMESTAMPTZ`   | nullable | Última compra observada.                               |
| `calculated_at`                  | `TIMESTAMPTZ`   | NN       | Momento de cálculo.                                    |

## 12.3 InventoryPlanningMetric

**Tabla:** `inventory_planning_metrics`

### Descripción

Conserva los indicadores calculados para planificación de inventario y abastecimiento por sucursal y producto.

### Atributos

| Atributo                     | Tipo            | Regla    | Descripción                     |
| ---------------------------- | --------------- | -------- | ------------------------------- |
| `id`                         | `UUID`          | PK, NN   | Identificador.                  |
| `company_id`                 | `UUID`          | NN       | Empresa.                        |
| `branch_id`                  | `UUID`          | NN       | Sucursal.                       |
| `company_product_id`         | `UUID`          | NN       | Producto.                       |
| `calculation_window_days`    | `INTEGER`       | NN       | Ventana utilizada.              |
| `average_daily_demand`       | `NUMERIC(18,4)` | nullable | Demanda diaria promedio.        |
| `demand_stddev`              | `NUMERIC(18,4)` | nullable | Desviación estándar de demanda. |
| `average_lead_time_hours`    | `NUMERIC(12,2)` | nullable | Lead time promedio utilizado.   |
| `safety_stock`               | `NUMERIC(18,4)` | nullable | Stock de seguridad calculado.   |
| `reorder_point`              | `NUMERIC(18,4)` | nullable | Punto de reorden calculado.     |
| `recommended_order_quantity` | `NUMERIC(18,4)` | nullable | Cantidad recomendada.           |
| `calculation_method`         | `VARCHAR(40)`   | NN       | Método de cálculo aplicado.     |
| `calculated_at`              | `TIMESTAMPTZ`   | NN       | Momento de cálculo.             |

### Reglas

- Estos valores son resultados calculados y no sustituyen la configuración de `InventoryPolicy`.
- Cuando el saldo sea igual o inferior al ROP, el sistema puede generar alerta, recomendación y, si la política lo permite, una compra `DRAFT`.

## 12.4 InventoryTurnoverMetric

**Tabla:** `inventory_turnover_metrics`

### Descripción

Proyección del indicador de rotación de inventario utilizando costo de ventas e inventario promedio valorizado.

### Atributos

| Atributo                  | Tipo            | Regla    | Descripción                                  |
| ------------------------- | --------------- | -------- | -------------------------------------------- |
| `id`                      | `UUID`          | PK, NN   | Identificador.                               |
| `company_id`              | `UUID`          | NN       | Empresa.                                     |
| `branch_id`               | `UUID`          | nullable | Sucursal; nulo para consolidado empresarial. |
| `company_product_id`      | `UUID`          | nullable | Producto; nulo para consolidado.             |
| `period_start`            | `DATE`          | NN       | Inicio del periodo.                          |
| `period_end`              | `DATE`          | NN       | Fin del periodo.                             |
| `cost_of_goods_sold`      | `NUMERIC(18,2)` | NN       | Costo de ventas del periodo.                 |
| `average_inventory_value` | `NUMERIC(18,2)` | NN       | Inventario promedio valorizado.              |
| `turnover_ratio`          | `NUMERIC(18,6)` | nullable | Rotación calculada.                          |
| `interpretation`          | `VARCHAR(20)`   | nullable | `HIGH`, `NORMAL`, `LOW` u `OBSOLETE`.        |
| `calculated_at`           | `TIMESTAMPTZ`   | NN       | Momento de cálculo.                          |

## 12.5 ProductABCClassification

**Tabla:** `product_abc_classifications`

### Descripción

Conserva la clasificación ABC histórica calculada por periodo. No se almacena como un atributo permanente de `CompanyProduct` porque puede cambiar con el comportamiento económico.

### Atributos

| Atributo                  | Tipo            | Regla    | Descripción                            |
| ------------------------- | --------------- | -------- | -------------------------------------- |
| `id`                      | `UUID`          | PK, NN   | Identificador.                         |
| `company_id`              | `UUID`          | NN       | Empresa.                               |
| `branch_id`               | `UUID`          | nullable | Sucursal; nulo para consolidado.       |
| `company_product_id`      | `UUID`          | NN       | Producto.                              |
| `period_start`            | `DATE`          | NN       | Inicio del periodo.                    |
| `period_end`              | `DATE`          | NN       | Fin del periodo.                       |
| `economic_value`          | `NUMERIC(18,2)` | NN       | Valor económico utilizado para Pareto. |
| `contribution_percentage` | `NUMERIC(7,4)`  | NN       | Participación individual.              |
| `cumulative_percentage`   | `NUMERIC(7,4)`  | NN       | Participación acumulada.               |
| `abc_class`               | `CHAR(1)`       | NN, CK   | `A`, `B` o `C`.                        |
| `calculated_at`           | `TIMESTAMPTZ`   | NN       | Momento de cálculo.                    |

# 13. Workflow DB

## 13.1 Alert

**Tabla:** `alerts`  
**Naturaleza:** operacional, privada y trazable.  
**Servicio propietario:** Workflow Service.

### Descripción

Representa una condición que requiere atención humana o automática por ejemplo margen bajo, stock de seguridad alcanzado o inventario igual o inferior al punto de reorden.

Una alerta no equivale a una autorización ni sustituye a `AuditEvent`.

### Atributos

| Atributo                  | Tipo          | Regla         | Descripción                                       |
| ------------------------- | ------------- | ------------- | ------------------------------------------------- |
| `id`                      | `UUID`        | PK, NN        | Identificador.                                    |
| `company_id`              | `UUID`        | REF, NN       | Empresa.                                          |
| `branch_id`               | `UUID`        | REF, nullable | Sucursal relacionada.                             |
| `alert_type`              | `VARCHAR(50)` | NN            | Tipo de alerta.                                   |
| `severity`                | `VARCHAR(20)` | NN, CK        | `INFO`, `WARNING`, `CRITICAL`.                    |
| `entity_type`             | `VARCHAR(60)` | NN            | Tipo de entidad origen.                           |
| `entity_id`               | `UUID`        | NN            | Entidad origen.                                   |
| `message`                 | `TEXT`        | NN            | Mensaje funcional.                                |
| `status`                  | `VARCHAR(20)` | NN, CK        | `OPEN`, `ACKNOWLEDGED`, `RESOLVED` o `DISMISSED`. |
| `correlation_id`          | `UUID`        | nullable      | Flujo distribuido.                                |
| `created_at`              | `TIMESTAMPTZ` | NN            | Creación.                                         |
| `acknowledged_by_user_id` | `UUID`        | REF, nullable | Usuario que reconoce.                             |
| `acknowledged_at`         | `TIMESTAMPTZ` | nullable      | Reconocimiento.                                   |
| `resolved_at`             | `TIMESTAMPTZ` | nullable      | Resolución.                                       |

## 13.2 ApprovalRequest

**Tabla:** `approval_requests`  
**Naturaleza:** operacional, privada y auditable.  
**Servicio propietario:** Workflow Service.

### Descripción

Representa una decisión que requiere autorización explícita, inicialmente aplicable a ventas por debajo del margen mínimo cuando `ProductPricingPolicy.below_minimum_action = REQUIRE_APPROVAL`.

### Atributos

| Atributo               | Tipo          | Regla         | Descripción                                      |
| ---------------------- | ------------- | ------------- | ------------------------------------------------ |
| `id`                   | `UUID`        | PK, NN        | Identificador.                                   |
| `company_id`           | `UUID`        | REF, NN       | Empresa.                                         |
| `branch_id`            | `UUID`        | REF, nullable | Sucursal.                                        |
| `request_type`         | `VARCHAR(50)` | NN            | Tipo de autorización.                            |
| `entity_type`          | `VARCHAR(60)` | NN            | Entidad afectada.                                |
| `entity_id`            | `UUID`        | NN            | Identificador de la entidad.                     |
| `requested_by_user_id` | `UUID`        | REF, NN       | Solicitante.                                     |
| `reason`               | `TEXT`        | NN            | Justificación.                                   |
| `context_snapshot`     | `JSONB`       | nullable      | Datos relevantes de la decisión.                 |
| `status`               | `VARCHAR(20)` | NN, CK        | `PENDING`, `APPROVED`, `REJECTED` o `CANCELLED`. |
| `resolved_by_user_id`  | `UUID`        | REF, nullable | Usuario que resuelve.                            |
| `resolution_reason`    | `TEXT`        | nullable      | Motivo de aprobación o rechazo.                  |
| `requested_at`         | `TIMESTAMPTZ` | NN            | Solicitud.                                       |
| `resolved_at`          | `TIMESTAMPTZ` | nullable      | Resolución.                                      |
| `correlation_id`       | `UUID`        | nullable      | Flujo distribuido.                               |

### Reglas y restricciones

- Una solicitud `PENDING` no puede considerarse autorizada por ausencia de respuesta.
- La resolución debe producir un evento auditable.
- La existencia de una alerta asociada es opcional y no cambia el estado de autorización.

# 15. Entidades técnicas por servicio

## 15.1 OutboxEvent

**Tabla:** `outbox_events`  
**Naturaleza:** técnica.  
**Servicio propietario:** Cada servicio productor.

### Descripción

Es una tabla técnica que evita que un microservicio guarde correctamente una operación en su base de datos, pero falle al informar ese cambio a los demás servicios.

Almacena eventos que un microservicio debe publicar en RabbitMQ.

Se guarda dentro de la misma transacción local que el cambio de negocio.

Esto evita persistir una operación sin conservar el evento necesario para informar a otros servicios.

Un publicador independiente envía los eventos pendientes y actualiza su estado.

### Atributos

| Atributo         | Tipo           | Regla           | Descripción                        |
| ---------------- | -------------- | --------------- | ---------------------------------- |
| `id`             | `UUID`         | PK, NN          | Identificador.                     |
| `event_id`       | `UUID`         | NN, UQ          | Identificador global del evento.   |
| `event_type`     | `VARCHAR(150)` | NN              | Tipo versionado.                   |
| `event_version`  | `SMALLINT`     | NN              | Versión.                           |
| `aggregate_type` | `VARCHAR(80)`  | NN              | Tipo de agregado.                  |
| `aggregate_id`   | `UUID`         | NN              | Agregado afectado.                 |
| `company_id`     | `UUID`         | nullable        | Empresa.                           |
| `payload`        | `JSONB`        | NN              | Contenido.                         |
| `status`         | `VARCHAR(20)`  | NN, CK          | `PENDING`, `PUBLISHED` o `FAILED`. |
| `attempt_count`  | `INTEGER`      | NN, DEFAULT `0` | Intentos.                          |
| `occurred_at`    | `TIMESTAMPTZ`  | NN              | Momento funcional.                 |
| `published_at`   | `TIMESTAMPTZ`  | nullable        | Publicación.                       |
| `next_retry_at`  | `TIMESTAMPTZ`  | nullable        | Próximo intento.                   |

## 15.2 InboxMessage

**Tabla:** `inbox_messages`  
**Naturaleza:** técnica.  
**Servicio propietario:** Cada servicio consumidor.

### Descripción

Es la tabla técnica que usa un microservicio cuando recibe eventos desde RabbitMQ para evitar procesar el mismo evento más de una vez.

Registra eventos recibidos por un consumidor y garantiza idempotencia.

Si RabbitMQ entrega el mismo evento de nuevo activando la restricción única sobre `event_id` permite detectar que ya fue recibido y evita repetir el efecto de negocio.

### Atributos

| Atributo        | Tipo           | Regla    | Descripción              |
| --------------- | -------------- | -------- | ------------------------ |
| `id`            | `UUID`         | PK, NN   | Identificador.           |
| `event_id`      | `UUID`         | NN, UQ   | Evento recibido.         |
| `event_type`    | `VARCHAR(150)` | NN       | Tipo.                    |
| `producer`      | `VARCHAR(80)`  | NN       | Servicio emisor.         |
| `payload`       | `JSONB`        | NN       | Contenido.               |
| `status`        | `VARCHAR(20)`  | NN, CK   | Estado de procesamiento. |
| `received_at`   | `TIMESTAMPTZ`  | NN       | Recepción.               |
| `processed_at`  | `TIMESTAMPTZ`  | nullable | Procesamiento.           |
| `error_details` | `JSONB`        | nullable | Error.                   |

## 15.3 IdempotencyKey

**Tabla:** `idempotency_keys`  
**Naturaleza:** técnica.  
**Servicio propietario:** Servicios con comandos críticos.

### Descripción

Sirve para evitar que una misma solicitud HTTP produzca dos veces el mismo efecto, aunque el frontend la envíe repetidamente.

Si el cliente reintenta una confirmación después de un fallo de red, el servicio reutiliza el resultado anterior y no crea una segunda operación ni modifica inventario nuevamente.

### Atributos

| Atributo          | Tipo           | Regla    | Descripción                           |
| ----------------- | -------------- | -------- | ------------------------------------- |
| `id`              | `UUID`         | PK, NN   | Identificador.                        |
| `key`             | `VARCHAR(150)` | NN       | Clave enviada por el cliente.         |
| `company_id`      | `UUID`         | NN       | Empresa.                              |
| `operation`       | `VARCHAR(100)` | NN       | Operación protegida.                  |
| `request_hash`    | `VARCHAR(128)` | NN       | Hash de la solicitud.                 |
| `response_status` | `INTEGER`      | nullable | Código HTTP guardado.                 |
| `response_body`   | `JSONB`        | nullable | Respuesta guardada.                   |
| `status`          | `VARCHAR(20)`  | NN, CK   | `PROCESSING`, `COMPLETED` o `FAILED`. |
| `expires_at`      | `TIMESTAMPTZ`  | NN       | Vencimiento.                          |
| `created_at`      | `TIMESTAMPTZ`  | NN       | Creación.                             |
| `updated_at`      | `TIMESTAMPTZ`  | NN       | Modificación.                         |
