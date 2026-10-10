# Ejercicio 1 — Configuración de la empresa: organizaciones, personas, empresas, sucursales y usuarios operativos

[← Recorrido completo](../README.md)

**Datos:** ficticios, con el `RUN_ID` de la corrida en nombres y códigos (`<RUN_ID>`).

## Orden de ejecución

Ejecute los archivos en este orden; cada paso usa los `id` guardados en los anteriores (y en los ejercicios previos).

| Paso | Archivo | Qué hace | Llamadas | Deja guardado |
| --- | --- | --- | --- | --- |
| 01 | [01-consultar-los-datos-de-referencia.md](01-consultar-los-datos-de-referencia.md) | Consultar los datos de referencia | 4 | `<CIUDAD>`, `<DEPARTAMENTO>`, `<PAIS_CO>`, `<PATRON_CC>`, `<PATRON_NIT>` |
| 02 | [02-registrar-las-organizaciones.md](02-registrar-las-organizaciones.md) | Registrar las organizaciones | 3 | `<ORG_EMPRESA_A>`, `<ORG_EMPRESA_B>`, `<ORG_PROVEEDOR>` |
| 03 | [03-registrar-las-personas.md](03-registrar-las-personas.md) | Registrar las personas | 8 | `<PERSONA_ADMIN>`, `<PERSONA_CLIENTE>`, `<PERSONA_COMPRAS>`, `<PERSONA_CONSULTA>`, `<PERSONA_INVENTARIO>`, `<PERSONA_REPORTES>`, `<PERSONA_SUPERVISOR>`, `<PERSONA_VENTAS>` |
| 04 | [04-registrar-las-empresas.md](04-registrar-las-empresas.md) | Registrar las empresas | 2 | `<EMPRESA_A>`, `<EMPRESA_B>` |
| 05 | [05-registrar-las-sucursales.md](05-registrar-las-sucursales.md) | Registrar las sucursales | 2 | `<SUCURSAL_A1>`, `<SUCURSAL_B1>`, `<ZONA_A1>`, `<ZONA_B1>` |
| 06 | [06-registrar-los-usuarios-operativos.md](06-registrar-los-usuarios-operativos.md) | Registrar los usuarios operativos | 7 | `<USUARIO_ADMIN>`, `<USUARIO_COMPRAS>`, `<USUARIO_CONSULTA>`, `<USUARIO_INVENTARIO>`, `<USUARIO_REPORTES>`, `<USUARIO_SUPERVISOR>`, `<USUARIO_VENTAS>` |
| 07 | [07-asignar-sucursales.md](07-asignar-sucursales.md) | Asignar sucursales | 5 | `<ASIGNACION_ADMIN>`, `<ASIGNACION_COMPRAS>`, `<ASIGNACION_INVENTARIO>`, `<ASIGNACION_SUPERVISOR>`, `<ASIGNACION_VENTAS>` |
| 08 | [08-comprobar-el-contexto-operativo.md](08-comprobar-el-contexto-operativo.md) | Comprobar el contexto operativo | 5 | — |

Usuarios y permisos de este ejercicio: [USUARIOS.md](USUARIOS.md).
