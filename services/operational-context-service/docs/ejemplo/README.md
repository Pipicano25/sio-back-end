# Ejercicios de uso — Operational Context Service

Ejercicios paso a paso para registrar y consultar empresas, sucursales, usuarios operativos,
asignaciones a sucursales y asesores con la API `v1` de `operational-context-service`, y para ver qué
usuario de prueba puede ejecutar cada llamada (Principio XXII de la Constitución).

Cada ejercicio es independiente: puede ejecutarse en una base nueva. Todos se validan
automáticamente con `pytest tests/examples` (base de pruebas; Party Identity, Geography y la Admin
API de Keycloak simulados): si la API, un permiso o una regla cambian, la prueba falla hasta que el ejercicio y esta
documentación se actualicen.

## Datos

No existe una fuente del sistema anterior para empresas, sucursales, usuarios ni asesores. **Todos
los datos son ficticios**: organizaciones, personas, direcciones, correos, teléfonos y nombres de
sucursal son inventados y no corresponden a empresas ni personas reales. Las cuentas de Keycloak son
los usuarios de prueba del realm (`supervisor.test`, `compras.test`, …).

La empresa **no guarda** NIT, razón social ni nombre comercial: esos datos legales pertenecen a
**Party Identity Service** y la empresa solo guarda el `id` de su organización. En un entorno real
la organización se registra allá con datos tomados de una fuente oficial (RUT, registro mercantil
RUES); nunca se inventan.

## Antes de empezar

1. **Servicio** en ejecución en `http://localhost:8004` (ver el `README.md` del servicio).
2. **Party Identity Service** en `http://localhost:8002` con la organización de cada ejercicio
   registrada, y **Geography Service** en `http://localhost:8000` con los datos de Colombia cargados.
   Operational Context valida contra ellos la organización y la ubicación al crear o cambiar esas
   referencias. Para los ejercicios 4 a 6, las personas de cada ejercicio deben existir en Party
   Identity y el realm debe incluir el cliente técnico `operational-context-service` (Keycloak Admin
   API de solo lectura).
3. **Token** de Keycloak (`http://localhost:8081`, realm `sio`). La contraseña de los usuarios de
   prueba es la variable `KEYCLOAK_TEST_USER_PASSWORD` de `infrastructure/.env`:

   ```bash
   TOKEN=$(python services/get_token.py admin)
   ```

   Detalle por usuario y permiso en [usuarios-y-permisos.md](usuarios-y-permisos.md).

## Convenciones de lectura

- Las rutas de Operational Context son relativas a `http://localhost:8004`. Las llamadas a otros
  servicios se marcan como **Otro servicio** y muestran su URL completa.
- `<NOMBRE>` es un valor guardado en un paso anterior (por ejemplo `<ORG_EMPRESA>` o `<EMPRESA>`):
  cada paso indica qué guardar y cada `ORDEN.md` lista todas las variables.
- Las respuestas se muestran **abreviadas**: se omiten campos de auditoría (`created_at`,
  `created_by`, …) y los `id` generados se muestran como `<id generado>` o con el nombre de su
  variable.
- Los errores siguen RFC 9457 (`application/problem+json`) con `code`
  (`OPERATIONAL_CONTEXT.<CAUSA>`) y `trace_id`.

## Ejercicios

| Ejercicio | Qué caso distinto cubre |
| --- | --- |
| [1 — Empresa con sede](1-empresa-con-sede/ORDEN.md) | Empresa vinculada a su organización, ubicación coherente de la sede operativa principal, modificación con **versión** y **organización inexistente** |
| [2 — Sucursales](2-sucursales/ORDEN.md) | Código único por empresa, zona horaria **heredada** frente a la propia, **código duplicado**, **ubicación incoherente** y **cambio de código** |
| [3 — Inactivación](3-inactivacion/ORDEN.md) | Inactivar la empresa **sin cascada**, efecto en la sucursal (`company_status`), alta rechazada, reactivación y transición repetida |
| [4 — Usuarios operativos](4-usuarios-operativos/ORDEN.md) | Membresías por `username`, **duplicado activo**, **cuenta técnica** rechazada, la **misma persona en dos empresas** e inactivación sin afectar la otra empresa |
| [5 — Sucursales y acceso](5-sucursales-y-acceso/ORDEN.md) | Asignación a sucursales, `GET /operational-access` por la **vía técnica** con permiso y cada **causa de denegación** |
| [6 — Asesores](6-asesores/ORDEN.md) | Asesor principal, **segundo principal** rechazado, asesor no principal, **cambio de asesor principal** atómico e historial |

## Aislamiento por empresa (Fase B)

El permiso de Keycloak dice **qué** puede hacer un usuario; la **membresía** dice **en qué
empresas**. Salvo `admin.test` (alcance de plataforma por `perm:all:all:all`), los usuarios solo ven
y operan las empresas donde tienen una membresía `ACTIVE`: fuera de ellas, las URL marcadas con 🔒
responden `404`, igual que un `id` inexistente. Por eso, en los ejercicios 1 a 3, los usuarios de
lectura reciben `404` al consultar empresas de las que no son miembros.

## Usuarios y permisos

- [usuarios-y-permisos.md](usuarios-y-permisos.md): cómo se evalúan los permisos, los usuarios de
  prueba, cómo obtener el token de cada uno y la matriz de todas las URL usadas.
- Cada ejercicio tiene su `USUARIOS.md` con el resumen por usuario y ejemplos permitidos y
  rechazados.
