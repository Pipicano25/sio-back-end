# Ejemplos de uso de purchase-service

Ejercicios validados (Constitución, Principio XXII) que muestran cómo registrar, confirmar y anular
compras, cómo funciona la numeración por período y cómo se registran los hitos logísticos.

- Los datos son **ficticios** y están marcados como tales; los identificadores y el reloj (5 de
  noviembre de 2026) son fijos para que los documentos sean estables.
- Cada carpeta es un ejercicio independiente: `ORDEN.md` (pasos y variables), `00-datos-ficticios.md`,
  un archivo por paso y `USUARIOS.md` (qué usuario puede ejecutar cada paso).
- `usuarios-y-permisos.md` resume los permisos de cada usuario de prueba y la matriz de URL.
- Los documentos se **generan y verifican** con `tests/examples/test_examples.py` contra la API y la base
  de pruebas; las dependencias (Operational Context, Commercial Relationship, Product Catalog, Party
  Identity, Payment Reference e Inventory) se simulan con sus dobles. Para regenerarlos:

  ```bash
  PURCHASE_EXAMPLES_WRITE=1 .venv/Scripts/python.exe -m pytest tests/examples
  ```

## Requisitos para reproducirlos contra el entorno integrado

- Plataforma `sio` y los proyectos Compose de las dependencias y de `purchase-service` levantados.
- Tokens de usuario con la contraseña de la variable `KEYCLOAK_TEST_USER_PASSWORD` (nunca en estos
  documentos). Ver `usuarios-y-permisos.md`.
- El usuario debe tener asignación `ACTIVE` a la sucursal de la compra en Operational Context para
  escribir; el permiso por comodín no la sustituye.

## Convenciones

- `<VARIABLE>`: valor guardado de una respuesta anterior (ver `ORDEN.md`).
- `<asignado por el servicio>`: identificadores y momentos que asigna Purchase o Inventory en cada
  ejecución.
- Los importes van como cadenas decimales: cantidades y costos unitarios con 4 decimales, montos con 2.

## Ejercicios

| Carpeta | Contenido |
| --- | --- |
| [1-secuencias](1-secuencias/ORDEN.md) | Secuencia mensual, contadores por período, una sola activa por alcance |
| [2-borrador](2-borrador/ORDEN.md) | Borrador con caja de 12, línea adicional, versión vieja, `409` vs `422` |
| [3-confirmacion](3-confirmacion/ORDEN.md) | Inventory caído, reintento con la misma clave, repetición idempotente |
| [4-compra-retroactiva](4-compra-retroactiva/ORDEN.md) | Compra de octubre confirmada en noviembre: contador de octubre |
| [5-anulacion](5-anulacion/ORDEN.md) | Anular borrador, anular confirmada (reverso exacto), rechazo por consumo |
| [6-hitos](6-hitos/ORDEN.md) | Hitos, rechazo fuera de orden, línea de tiempo y lead time |
| [7-consultas](7-consultas/ORDEN.md) | Listado filtrado y aislamiento por empresa |
