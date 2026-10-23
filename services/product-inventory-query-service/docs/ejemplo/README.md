# Ejercicios de uso de product-inventory-query-service

Ejercicios paso a paso, ejecutables y validados automáticamente por
`tests/examples/test_examples.py` (Constitución, Principio XXII). Todo lo que hay en estas carpetas,
salvo este archivo, lo genera esa prueba: si cambia un ejercicio, un contrato o la plantilla del
realm, se regenera con `PRODUCT_INVENTORY_QUERY_EXAMPLES_WRITE=1 pytest tests/examples`.

| Ejercicio | Qué muestra |
| --- | --- |
| [1-catalogo-con-imagen-y-precio](1-catalogo-con-imagen-y-precio/ORDEN.md) | Búsqueda con imagen (ruta R-B), dos páginas con cursor, una presentación sin precio en la lista e `include_images=true` |
| [2-cambio-de-filtros-y-cursor](2-cambio-de-filtros-y-cursor/ORDEN.md) | Reinicio automático por `FILTERS_CHANGED`, `PAGE_SIZE_CHANGED` y `SORT_CHANGED`, y cursor alterado (`422`) |
| [3-inventario-multisucursal](3-inventario-multisucursal/ORDEN.md) | Consolidado de la empresa, sucursal sin asignación (A-08), equivalencias, `NOT_REGISTERED` y sucursal de otra empresa (`404`) |
| [4-bajo-stock](4-bajo-stock/ORDEN.md) | Pares producto–sucursal bajo el mínimo en orden `shortfall:desc`; igual al mínimo y mínimo 0 no aparecen |
| [5-resumen](5-resumen/ORDEN.md) | Indicadores operativos por propietario (categorías A a E), de la empresa y de una sucursal, sin valoración |
| [6-permisos](6-permisos/ORDEN.md) | `ventas` sin mínimos, `inventario` sin precios, filtro no autorizado (`403`) y `compras` sin acceso |

Permisos, usuarios y cómo obtener los tokens: [usuarios-y-permisos.md](usuarios-y-permisos.md).

## Requisitos para ejecutarlos a mano

- Entorno integrado levantado: Keycloak (reconstruido desde la plantilla del realm), Operational
  Context, Commercial Relationship, Product Catalog, Inventory y product-inventory-query-service
  (`http://localhost:8112`).
- La empresa, las sucursales y los productos de `00-datos-ficticios.md` deben existir en esos
  servicios; en el entorno integrado se usan sus propios identificadores en lugar de los de los
  ejercicios.
- Token del usuario de prueba con la contraseña de la variable `KEYCLOAK_TEST_USER_PASSWORD`. Nunca
  se escriben contraseñas ni tokens en estos documentos.
- Las imágenes son de cada presentación (spec 024): `presentations[].has_image`, `asset_id` e
  `image_url`, y `presentations[].images` solo con `include_images=true`. El producto y
  `low-stock-products` no traen imágenes.
- La URL de imagen (`image_url`) solo existe si Product Catalog tiene configurada la ruta pública
  de imágenes; sin ella, `image_url` es `null` aunque `has_image` sea `true`.

## Convenciones

- Datos **ficticios**: crema dental, jarabe y analgésicos en tabletas; ningún NIT, razón social ni
  dato de una empresa real.
- Cantidades en la unidad base del producto, con 4 decimales; precios como cadena decimal, con la
  moneda que informa Commercial Relationship. El servicio no devuelve valoración económica.
- `<CURSOR>`: el `next_cursor` guardado de un paso anterior (ver `ORDEN.md`). Un cursor vence a los
  15 minutos y solo vale con los mismos filtros, orden y `page_size`.
- `<asignado por el servicio>`: valor que cambia en cada ejecución (`resolved_at`, `trace_id` y los
  cursores que no se usan después).
- Las consultas solo leen: ningún ejercicio cambia datos, así que se pueden repetir en cualquier
  orden salvo los pasos que usan `<CURSOR>`.
- Cada archivo de paso indica el método y la URL, el permiso, qué usuarios pueden y cuáles no (y
  por qué), la justificación y la respuesta esperada.
