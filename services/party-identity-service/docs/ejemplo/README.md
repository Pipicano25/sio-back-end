# Ejercicios de uso — Party Identity Service

Ejercicios paso a paso para crear y consultar reglas de identificación, personas, organizaciones,
perfiles de contacto, personas de contacto y representantes legales con la API `v1` de
`party-identity-service`, y para ver qué usuario de prueba puede ejecutar cada llamada
(Principio XXII de la Constitución).

Cada ejercicio es independiente: puede ejecutarse en una base nueva. Todos se validan
automáticamente con `pytest tests/examples` (base de pruebas, Geography y Operational Context
simulados): si la API, un
permiso o una regla cambian, la prueba falla hasta que el ejercicio y esta documentación se
actualicen.

## Datos

No existe una fuente del sistema anterior para identidades ni contactos. **Todos los datos son
ficticios**: nombres, cédulas, NIT, razones sociales, correos, teléfonos y direcciones son inventados y no corresponden a personas ni empresas
reales. En un entorno real esos datos se toman de una fuente oficial (documento de identidad, RUT,
registro mercantil RUES); nunca se inventan, porque el registro de identidades es global y lo usan
todas las empresas.

## Antes de empezar

1. **Servicio** en ejecución en `http://localhost:8002` (ver el `README.md` del servicio).
2. **Reglas iniciales** cargadas:
   `python -m party_identity_service.seed load --country-id <id de Colombia en su Geography>`
   (o sin `--country-id`, en modo Geography). Crean las 8 reglas de Colombia (`CC`, `TI`, `RC`, `CE`,
   `NIT`).
3. **Geography Service** en `http://localhost:8000` para consultar el país (y la división y la ciudad de
   las direcciones) y para que Party Identity los valide.
4. **Operational Context Service** en `http://localhost:8004` (ejercicios 4 y 5): para confirmar un perfil
   de contacto, el usuario debe tener una **membresía `ACTIVE`** en la empresa indicada (ver el ejercicio 4
   de `services/operational-context-service/docs/ejemplo/`). Party Identity la comprueba con su propio
   cliente técnico; el usuario no necesita permisos de Operational Context.
5. **Token** de Keycloak (`http://localhost:8081`, realm `sio`). La contraseña de los usuarios de
   prueba es la variable `KEYCLOAK_TEST_USER_PASSWORD` de `infrastructure/.env`:

   ```bash
   TOKEN=$(python services/get_token.py admin)
   ```

   Detalle por usuario y permiso en [usuarios-y-permisos.md](usuarios-y-permisos.md).

## Convenciones de lectura

- Las rutas son relativas a `http://localhost:8002`.
- `<NOMBRE>` es un valor guardado en un paso anterior (por ejemplo `<PAIS_CO>` o `<PERSONA_ANA>`):
  cada paso indica qué guardar y cada `ORDEN.md` lista todas las variables.
- Las respuestas se muestran **abreviadas**: se omiten campos de auditoría (`created_at`,
  `created_by`, …) y los `id` generados se muestran como `<id generado>` o con el nombre de su
  variable.
- Los errores siguen RFC 9457 (`application/problem+json`) con `code` (`PARTY_IDENTITY.<CAUSA>`) y
  `trace_id`.

## Ejercicios

| Ejercicio | Qué caso distinto cubre |
| --- | --- |
| [1 — Reglas de identificación](1-reglas-de-identificacion/ORDEN.md) | Crear una regla, rechazos (`409` duplicada, `422` patrón inválido), corregir en sitio, **nueva versión** al cambiar el patrón y **retiro** sin borrar |
| [2 — Personas](2-personas/ORDEN.md) | Validación por reglas de formato y **edad**, duplicado, control de **versión**, verificación e **inactivación** con filtro por estado |
| [3 — Organizaciones](3-organizaciones/ORDEN.md) | Regla `NIT`, **país inexistente**, ciclo **inactivar → reactivar** y transición repetida; quién puede cada acción |
| [4 — Perfil de contacto de una organización](4-perfil-de-organizacion/ORDEN.md) | Confirmación desde una empresa, **no-op**, **nueva versión**, historial, geografía inválida, **usuario sin membresía**, **dependencia caída** y **cierre** (y su repetición); `compras` lee, `reportes`/`consulta` reciben `403` |
| [5 — Perfil de contacto de una persona](5-perfil-de-persona/ORDEN.md) | Cliente persona natural sin dirección; **inactivar la persona** no cierra el perfil pero impide versiones nuevas |
| [6 — Personas de contacto](6-personas-de-contacto/ORDEN.md) | Contacto vinculado a una persona, **principal único**, `409` al crear otro, **`set-primary`** e inactivación; consulta Provider por `id` |
| [7 — Sectores económicos](7-sectores-economicos/ORDEN.md) | Árbol **CIIU Rev. 5 A.C.** del `seed` (sección → clase), clasificación propia, **`409` al inactivar un sector con hijos activos**, asignación a una organización, **`set-primary`** y cierre con historial |
| [8 — Representantes legales](8-representantes-legales/ORDEN.md) | Primer `PRIMARY` con **`set-primary`**, `409` por alta ordinaria, sustitución, suplente con **referencia documental** y cierre; dato sensible (`403` para `compras`) |

El ejercicio 7 necesita el catálogo CIIU cargado: `python -m party_identity_service.seed
load-business-sectors` (datos oficiales del DANE; fuente y SHA-256 en
`src/party_identity_service/seed/data/ciiu_rev5_ac/SOURCE.md`).

## Usuarios y permisos

- [usuarios-y-permisos.md](usuarios-y-permisos.md): cómo se evalúan los permisos, los usuarios de
  prueba, cómo obtener el token de cada uno y la matriz de todas las URL usadas.
- Cada ejercicio tiene su `USUARIOS.md` con el resumen por usuario y ejemplos permitidos y
  rechazados.
