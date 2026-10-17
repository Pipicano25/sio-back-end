# Validación integral del MVP de SIO (FASE 10)

Suite E2E automatizada de la feature 017 (`specs/017-mvp-integral-validation/`). Con un solo comando
verifica el entorno integrado y recorre, con los servicios reales y Keycloak real, el ciclo completo del
MVP: configuración → compras → inventario → ventas (precio por presentación: lista indicada y lista predeterminada; spec 019) → salida FIFO con costo y
margen → anulaciones → auditoría. Además comprueba el aislamiento entre empresas y los permisos, provoca
caídas controladas de dependencias restaurando siempre el entorno, valida la guía
[`docs/validacion-mvp/`](../../docs/validacion-mvp/README.md) y ejecuta la regresión integral contra una
línea base. Deja evidencia por cada uno de los 23 ítems de la FASE 10 del roadmap.

La suite **no** modifica servicios, librerías, infraestructura, bases de datos ni permisos: solo usa las
API públicas (`127.0.0.1`, puertos de [`docs/port-map.md`](../../docs/port-map.md)), lee bases y logs
para verificar (`SELECT`, `docker inspect`, `docker logs`) y detiene/arranca contenedores únicamente
durante las caídas. Nunca ejecuta `docker rm`, `docker compose down` ni `docker volume rm`.

## Barrera de aislamiento (obligatoria desde el 2026-10-16)

El recorrido **escribe** (empresas, personas, productos, compras, ventas) y la etapa de caídas detiene contenedores.
El 2026-10-16 una ejecución accidental contra el entorno integrado persistente creó datos de prueba en sus bases. Por
eso la suite solo se ejecuta contra la **pila aislada** `sio-it-*`:

- `SIO_TEST_TARGET=isolated` es obligatorio; sin esa variable la suite falla antes de crear el primer cliente HTTP.
- Las URL (`SIO_MVP_<SERVICIO>_URL` y `SIO_MVP_KEYCLOAK_TOKEN_URL`) deben llegar a puertos publicados por contenedores
  con la etiqueta `sio.integration.isolated=true` y el prefijo `sio-it-`; los valores por omisión (puertos 81xx y
  8081 del entorno persistente) se rechazan. `localhost` no basta.
- `docker stop`, `start` y `exec` solo se permiten sobre contenedores aislados, y `docker compose` queda bloqueado.

La barrera es `validation/isolation_guard.py` (compartida con las suites de integración de Purchase, Sales y Commercial
Relationship) y se prueba en `tests/unit/test_isolation_guard.py`. Las pruebas unitarias no la necesitan: se ejecutan
siempre con `pytest tests/unit` (no use `-m "not integration"`: esta suite no usa ese marcador y seleccionaría el
recorrido completo).

## Precondiciones

La pila aislada `sio-it-*` debe estar levantada con migraciones y seeds aplicados. La
etapa `preflight` verifica las precondiciones E-01..E-12 descritas en
[`quickstart.md`](../../specs/017-mvp-integral-validation/quickstart.md) (Docker, Keycloak con el realm
de la plantilla, 10 servicios sanos, migraciones en head, workers de auditoría, conciliadores, seeds,
Admin API de Operational Context, variables necesarias y, para la regresión, bases de pruebas). Si
alguna falla, la corrida termina con código `2` sin ejecutar nada más.

Variables (se leen del entorno o de `infrastructure/.env`; nunca se imprimen ni se copian):

| Variable | Uso |
| --- | --- |
| `KEYCLOAK_TEST_USER_PASSWORD` | Contraseña de los usuarios de prueba |
| `SALES_SERVICE_CLIENT_SECRET`, `PURCHASE_SERVICE_CLIENT_SECRET` | Comprobar que una identidad técnica no compra ni vende |
| `SIO_MVP_<SERVICIO>_URL` | Sobrescribir la URL base de un servicio (p. ej. `SIO_MVP_SALES_URL`) |
| `SIO_MVP_KEYCLOAK_TOKEN_URL` | URL del token de Keycloak |
| `SIO_MVP_AUDIT_WAIT_SECONDS` | Espera máxima de la entrega de eventos a Audit |
| `SIO_MVP_GUIDE_WRITE=1` | Regenerar la guía `docs/validacion-mvp/` |
| `SIO_MVP_PYTHON` | Intérprete (>= 3.12) con el que `run.sh` crea `.venv` |

## Comandos

Desde la raíz del repositorio (Git Bash en Windows, `bash` en Linux/macOS):

```bash
bash validation/mvp-e2e/run.sh --linea-base        # línea base de la regresión (una vez, antes de cambiar nada)
bash validation/mvp-e2e/run.sh                     # preflight + recorrido + seguridad + caidas + guia
bash validation/mvp-e2e/run.sh --todo              # lo anterior + regresion (≈ 2 h); obligatorio para el gate
bash validation/mvp-e2e/run.sh --etapa recorrido   # una sola etapa (repetible: --etapa a --etapa b)
bash validation/mvp-e2e/run.sh --sin-caidas        # omite la etapa caidas
bash validation/mvp-e2e/run.sh --restaurar         # solo arranca contenedores gestionados detenidos
```

`run.sh` crea `validation/mvp-e2e/.venv` si no existe (con `venv` o, si el Python del sistema no trae
`ensurepip`, con `uv`) e instala `pytest` y `httpx`.

Pruebas de la suite sin servicios:

```bash
validation/mvp-e2e/.venv/bin/python -m pytest validation/mvp-e2e/tests/unit -p no:cacheprovider          # Linux/macOS
validation/mvp-e2e/.venv/Scripts/python.exe -m pytest validation/mvp-e2e/tests/unit -p no:cacheprovider  # Windows
```

## Etapas

| Etapa | Contenido | Depende de |
| --- | --- | --- |
| `preflight` | Precondiciones E-01..E-12 | — |
| `recorrido` | Configuración (C-01..C-13), compras (P-01..P-03), ventas (V-01..V-07), anulaciones (A-01..A-03), auditoría (U-01, U-02) | `preflight` |
| `seguridad` | Aislamiento entre empresas y matriz de permisos S-01..S-07 | `recorrido` |
| `caidas` | O1, O2, O3, O4a, O4b, O5, O6 en serie, cada una restaurada antes de la siguiente | `recorrido` |
| `guia` | Guía versionada = guía generada; todos sus pasos ejecutados | `recorrido` |
| `regresion` | Suites completas de los 10 servicios y de `libs/` frente a `baseline.json` | `preflight` |

Sin `--todo` no se ejecuta `regresion` y la corrida **nunca** es elegible para el gate
`SIO MVP CORE READY` (`gate_eligible = false`, P-07).

## Informes

`validation/mvp-e2e/reports/<RUN_ID>/` (no versionado): `run.json`, `steps.jsonl`,
`audit-expected.json`, `audit-check.json`, `outages.json`, `regression.json`, `timings.json`,
`summary.json`, `summary.md` y `pytest-<etapa>.xml`. Formato en
[`contracts/evidence-format.md`](../../specs/017-mvp-integral-validation/contracts/evidence-format.md).
Ningún informe contiene contraseñas, tokens, secretos ni valores protegidos: el diario filtra
`Authorization`, secretos y los campos protegidos antes de escribir.

`baseline.json` (versionado) guarda la línea base de la regresión: conteos por servicio y suite e
identificadores de los fallos conocidos (los 6 de Geography, `list_all()`).

## Códigos de salida

| Código | Significado |
| --- | --- |
| `0` | Todas las etapas pedidas cumplen |
| `1` | Alguna prueba no cumple (ver `summary.md`) |
| `2` | `preflight` falló; no se ejecutó nada más |
| `3` | El entorno no pudo restaurarse por completo |

## Restauración

Al iniciar, `run.py` guarda el estado de los contenedores gestionados (`sio-*-service`, `sio-*-db`,
`sio-*-audit-outbox-worker`, `sio-*-reconciler`, `sio-keycloak`). Cada caída detiene un solo contenedor
y lo arranca en `finally`, esperando su salud (hasta 180 s). Al terminar —también por error o
`Ctrl+C`— arranca cualquier contenedor que estaba sano al inicio y quedó detenido. Si algo quedó
detenido tras una interrupción: `bash validation/mvp-e2e/run.sh --restaurar`.

## Guía del recorrido

Los pasos se describen una sola vez como datos en `scenario/steps.py`; de ellos se generan la ejecución
y la guía `docs/validacion-mvp/`. La etapa `guia` exige que la guía versionada sea la generada y que todos
sus pasos (recorrido y seguridad) se hayan ejecutado en la misma corrida. Tras cambiar un paso:

```bash
SIO_MVP_GUIDE_WRITE=1 bash validation/mvp-e2e/run.sh --etapa recorrido --etapa seguridad --etapa guia
```

## Brechas

Si una prueba falla por el comportamiento de un servicio, **no** se corrige el servicio ni se adapta la
aserción: se registra en `specs/017-mvp-integral-validation/gap-register.md` y se clasifica según
[`contracts/gap-classification.md`](../../specs/017-mvp-integral-validation/contracts/gap-classification.md)
(BLOQUEANTE / NO BLOQUEANTE) para la decisión del usuario. Si el error es de la suite, se corrige la
suite y se registra como desviación.
