#!/usr/bin/env bash
#
# SIO - Regeneración del entorno integrado
#
# El entorno se reparte en varios proyectos compose:
#   - "sio" (infrastructure/compose.yaml): solo infraestructura compartida
#     (Keycloak + su base, RabbitMQ) y la red sio-network;
#   - "<microservicio>" (infrastructure/services/<microservicio>.yaml): única
#     definición Compose del microservicio: su base propia, su base de pruebas
#     (perfil "test", este script no la levanta) y, si ya existe, su contenedor
#     de aplicación. Se unen a sio-network, así que "sio" se levanta primero.
#
# Si encuentra contenedores de microservicios aún dentro del proyecto "sio" o
# de un proyecto "sio-<microservicio>" (versiones anteriores del entorno), los
# elimina antes de levantar el proyecto vigente; los volúmenes conservan su
# nombre, así que la información no se pierde.
#
# Dos modos:
#
#   1) Restaurar solo Docker (--rebuild)
#                Conserva la información. Baja los contenedores (sin tocar los
#                volúmenes), reconstruye las imágenes, levanta todo y aplica
#                las migraciones pendientes. Keycloak conserva su realm: los
#                cambios en la plantilla del realm NO se aplican en este modo.
#
#   2) Docker completo con toda su información (--full)
#                BORRA la información actual. Baja los contenedores y elimina
#                sus volúmenes (bases de datos, Keycloak, RabbitMQ),
#                reconstruye, levanta (Keycloak reimporta el realm desde la
#                plantilla), migra desde cero y carga los datos iniciales en
#                orden: geography -> product-catalog -> party-identity (id de COL)
#
# Verificaciones previas (antes de bajar nada):
#   - carpetas ilegibles dentro de los servicios (p. ej. una .pytest_cache con
#     permisos rotos), que hacen fallar el build de la imagen;
#   - contenedores de otros proyectos compose con el mismo container_name: se
#     ofrece eliminarlos (solo el contenedor, nunca sus volúmenes);
#   - puertos del host definidos en infrastructure/.env (docs/port-map.md): se
#     ofrece detener los contenedores de otros proyectos que los publiquen y,
#     con el entorno abajo, falla si otro proceso los sigue ocupando, indicando
#     la variable a cambiar.
#
# Al final pregunta si los contenedores deben quedar levantados o detenidos.
#
# Uso (desde cualquier carpeta):
#   bash infrastructure/scripts/rebuild-all.sh                 # todo interactivo
#   bash infrastructure/scripts/rebuild-all.sh --rebuild       # restaurar solo Docker
#   bash infrastructure/scripts/rebuild-all.sh --full          # completo con información
#
# Opciones:
#   -y, --yes    no pedir confirmaciones (borrado y contenedores en conflicto)
#   --keep-up    dejar los contenedores levantados al terminar (sin preguntar)
#   --stop       detener los contenedores al terminar (sin preguntar)
#   --no-cache   construir las imágenes sin caché
#   --status     solo mostrar el resumen de contenedores y salir
#
# Al terminar (también si falla o se cancela a mitad de camino) muestra un
# resumen de lo realizado: cada paso con su resultado y duración, las acciones
# tomadas (conflictos, migraciones, datos cargados), los accesos y el estado de
# todos los contenedores del entorno.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(dirname "$SCRIPT_DIR")"
REPO_DIR="$(dirname "$INFRA_DIR")"
ENV_FILE="$INFRA_DIR/.env"
COMPOSE_FILE="$INFRA_DIR/compose.yaml"
STACKS_DIR="$INFRA_DIR/services"
INFRA_PROJECT=sio

# Git Bash (MSYS) convierte los argumentos que parecen rutas POSIX en rutas de
# Windows: "/app/services/..." llegaría al contenedor como
# "C:/Program Files/Git/app/services/...". Se desactiva esa conversión y las
# rutas locales que recibe docker se pasan ya en formato Windows (C:/...).
if command -v cygpath >/dev/null 2>&1; then
    ENV_FILE="$(cygpath -m "$ENV_FILE")"
    COMPOSE_FILE="$(cygpath -m "$COMPOSE_FILE")"
    STACKS_DIR="$(cygpath -m "$STACKS_DIR")"
    export MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*'
fi

MODE=""
FINAL_STATE=""
ASSUME_YES=false
BUILD_ARGS=()

for arg in "$@"; do
    case "$arg" in
        --rebuild) MODE=rebuild ;;
        --full) MODE=full ;;
        --keep-up) FINAL_STATE=up ;;
        --stop) FINAL_STATE=stop ;;
        -y|--yes) ASSUME_YES=true ;;
        --no-cache) BUILD_ARGS+=(--no-cache) ;;
        --status) MODE=status ;;
        *) echo "Error: argumento desconocido '$arg'" >&2; exit 2 ;;
    esac
done

# Microservicios con imagen propia (todos usan Alembic). Cada uno vive en el
# proyecto compose "<microservicio>" (infrastructure/services/).
SERVICES=(
    geography-service
    product-catalog-service
    party-identity-service
    operational-context-service
    commercial-relationship-service
    payment-reference-service
    audit-service
)

# Proyectos compose del entorno: primero la infraestructura, luego uno por
# cada archivo de infrastructure/services/ (incluye los que aún solo tienen base).
PROJECTS=("$INFRA_PROJECT")
for file in "$STACKS_DIR"/*.yaml; do
    [ -f "$file" ] && PROJECTS+=("$(basename "$file" .yaml)")
done

# --- Registro de lo realizado (para el resumen final) -----------------------
CURRENT_STEP=""
STEP_START=0
STEP_NAMES=()
STEP_RESULTS=()
STEP_TIMES=()
ACTIONS=()
CANCELLED=false
RUN_START=$(date +%s)
RUN_START_TEXT="$(date '+%Y-%m-%d %H:%M:%S')"

# Cierra el paso en curso con el resultado indicado.
finish_step() {
    [ -n "$CURRENT_STEP" ] || return 0
    STEP_NAMES+=("$CURRENT_STEP")
    STEP_RESULTS+=("$1")
    STEP_TIMES+=("$(( $(date +%s) - STEP_START ))")
    CURRENT_STEP=""
}

step() {
    finish_step OK
    CURRENT_STEP="$*"
    STEP_START=$(date +%s)
    echo
    echo "==> [$(( ${#STEP_NAMES[@]} + 1 ))] $*"
}

# Registra un paso que no aplica en este modo.
skip_step() {
    finish_step OK
    STEP_NAMES+=("$1")
    STEP_RESULTS+=("OMITIDO")
    STEP_TIMES+=("-")
}

# Registra una acción relevante para el resumen y la muestra.
note() {
    ACTIONS+=("$*")
    echo "  $*"
}

cancel() {
    CANCELLED=true
    echo "Cancelado: $*"
    exit 1
}

duration() {
    local s=$1
    if [ "$s" -ge 60 ]; then printf '%dm %02ds' $((s / 60)) $((s % 60)); else printf '%ds' "$s"; fi
}

# compose <proyecto> <args...>: docker compose sobre el archivo del proyecto.
# El nombre se pasa explícito para que ninguna COMPOSE_PROJECT_NAME heredada
# junte todos los servicios en un mismo proyecto.
compose() {
    local project=$1 file
    shift
    if [ "$project" = "$INFRA_PROJECT" ]; then
        file="$COMPOSE_FILE"
    else
        file="$STACKS_DIR/$project.yaml"
    fi
    docker compose --project-name "$project" --file "$file" --env-file "$ENV_FILE" "$@"
}

# Proyecto compose de un microservicio.
project_of() {
    echo "$1"
}

# Indica si un proyecto compose pertenece a este entorno.
is_own_project() {
    local project
    for project in "${PROJECTS[@]}"; do
        [ "$project" = "$1" ] && return 0
    done
    return 1
}

confirm() {
    [ "$ASSUME_YES" = true ] && return 0
    local answer
    read -r -p "$1 [y/N] " answer
    [[ "$answer" =~ ^[yYsS]$ ]]
}

[ -f "$ENV_FILE" ] || { echo "Error: no existe $ENV_FILE (cp .env.example .env)." >&2; exit 1; }

# shellcheck disable=SC1090
set -a; . "$ENV_FILE"; set +a
# Un COMPOSE_PROJECT_NAME heredado (p. ej. de un .env anterior) no debe
# imponerse sobre el "name:" de cada archivo.
unset COMPOSE_PROJECT_NAME

# Estado de todos los contenedores definidos en cada proyecto compose:
# levantados (✔), detenidos (■) y no iniciados (✘, nunca creados).
report_containers() {
    local project service name state health states
    local running=0 stopped=0 missing=0
    local lines=()

    for project in "${PROJECTS[@]}"; do
        lines+=("  $project")
        states="$(compose "$project" ps -a --format '{{.Service}}|{{.Name}}|{{.State}}|{{.Health}}' 2>/dev/null || true)"
        while read -r service; do
            [ -n "$service" ] || continue
            IFS='|' read -r _ name state health <<< "$(grep -E "^${service}\|" <<< "$states" | head -1)" || true
            if [ -z "${state:-}" ]; then
                missing=$((missing + 1))
                lines+=("$(printf '    ✘ %-30s %s' "$service" "no iniciado")")
            elif [ "$state" = running ]; then
                running=$((running + 1))
                lines+=("$(printf '    ✔ %-30s %-38s %s' "$service" "$name" "${health:-sin healthcheck}")")
            else
                stopped=$((stopped + 1))
                lines+=("$(printf '    ■ %-30s %-38s %s' "$service" "$name" "$state")")
            fi
            name=""; state=""; health=""
        done < <(compose "$project" config --services 2>/dev/null | sort)
    done

    echo "Contenedores (${#PROJECTS[@]} proyectos): levantados $running, detenidos $stopped, no iniciados $missing"
    for line in "${lines[@]}"; do echo "$line"; done
}

# Resumen completo de la ejecución: se muestra siempre al salir.
summary() {
    local status=$1
    local i result outcome mode_text var

    if [ "$status" -ne 0 ]; then
        if [ "$CANCELLED" = true ]; then finish_step CANCELADO; else finish_step FALLÓ; fi
    else
        finish_step OK
    fi

    case "$MODE" in
        rebuild) mode_text="Restaurar solo Docker (información conservada)" ;;
        full) mode_text="Docker completo con toda su información (regenerada desde cero)" ;;
        *) mode_text="${MODE:-sin definir}" ;;
    esac
    if [ "$status" -eq 0 ]; then outcome="COMPLETADO"
    elif [ "$CANCELLED" = true ]; then outcome="CANCELADO"
    else outcome="FALLÓ"
    fi

    echo
    echo "========================= Resumen de la ejecución ========================="
    echo "Modo:      $mode_text"
    echo "Resultado: $outcome"
    echo "Inicio:    $RUN_START_TEXT"
    echo "Fin:       $(date '+%Y-%m-%d %H:%M:%S')  (duración total: $(duration $(( $(date +%s) - RUN_START ))))"
    echo
    echo "Pasos:"
    for i in "${!STEP_NAMES[@]}"; do
        result="${STEP_RESULTS[$i]}"
        case "$result" in
            OK) result="✔ OK       " ;;
            OMITIDO) result="- OMITIDO  " ;;
            CANCELADO) result="■ CANCELADO" ;;
            *) result="✘ FALLÓ    " ;;
        esac
        if [ "${STEP_TIMES[$i]}" = "-" ]; then
            printf '  %2d. %s %8s  %s\n' $((i + 1)) "$result" "" "${STEP_NAMES[$i]}"
        else
            printf '  %2d. %s %8s  %s\n' $((i + 1)) "$result" "$(duration "${STEP_TIMES[$i]}")" "${STEP_NAMES[$i]}"
        fi
    done

    if [ "${#ACTIONS[@]}" -gt 0 ]; then
        echo
        echo "Acciones realizadas:"
        for i in "${ACTIONS[@]}"; do echo "  • $i"; done
    fi

    if [ "$status" -eq 0 ] && [ "$FINAL_STATE" = up ]; then
        echo
        echo "Accesos (docs/port-map.md):"
        printf '  %-29s %s\n' "Keycloak admin" "${KEYCLOAK_PUBLIC_URL}/admin  (realm: ${KEYCLOAK_REALM})"
        printf '  %-29s %s\n' "RabbitMQ management" "http://localhost:${RABBITMQ_MANAGEMENT_PORT}"
        for i in "${SERVICES[@]}"; do
            var="${i//-/_}"; var="${var^^}_PORT"
            printf '  %-29s http://localhost:%s\n' "$i" "${!var:-?}"
        done
    fi

    echo
    report_containers
    echo "==========================================================================="
}

if [ "$MODE" = status ]; then
    report_containers
    exit 0
fi

if [ -z "$MODE" ]; then
    echo "¿Qué deseas hacer?"
    echo "  1) Restaurar solo Docker: reconstruye y levanta los contenedores"
    echo "     conservando la información (bases, Keycloak, RabbitMQ)."
    echo "  2) Docker completo con toda su información: BORRA los datos actuales,"
    echo "     reconstruye, migra desde cero y carga los datos iniciales."
    read -r -p "Opción [1/2]: " option
    case "$option" in
        1) MODE=rebuild ;;
        2) MODE=full ;;
        *) echo "Cancelado."; exit 0 ;;
    esac
fi

if [ "$MODE" = full ]; then
    echo
    echo "Esto BORRARÁ los volúmenes de todos los proyectos del entorno"
    echo "(${PROJECTS[*]}):"
    echo "bases de datos, Keycloak y RabbitMQ, y los regenerará desde cero."
    confirm "¿Continuar?" || { echo "Cancelado."; exit 0; }
fi

trap 'summary $?' EXIT

# --- Verificaciones previas ---------------------------------------------------
# Se revisa todo antes de bajar nada, para no dejar el entorno a medias.

# Una carpeta que el usuario no puede leer (típicamente .pytest_cache creada
# como administrador o root) hace fallar el build cuando el Docker CLI corre en
# Linux/WSL ("failed to xattr ...: permission denied"), porque ese CLI lee la
# carpeta del Dockerfile. El Docker CLI de Windows (Git Bash, PowerShell) no se
# ve afectado: ahí solo se advierte.
step "Verificando permisos de las carpetas de los servicios"
UNREADABLE=()
for service in "${SERVICES[@]}"; do
    while read -r dir; do
        ls -A "$dir" >/dev/null 2>&1 || UNREADABLE+=("$dir")
    done < <(find "$REPO_DIR/services/$service" -maxdepth 2 -type d \
                -not -path '*/.venv/*' -not -path '*/.git/*' 2>/dev/null)
done
if [ "${#UNREADABLE[@]}" -gt 0 ]; then
    echo "Estas carpetas no se pueden leer:" >&2
    for dir in "${UNREADABLE[@]}"; do echo "  - $dir" >&2; done
    echo "Si son cachés (.pytest_cache, __pycache__...), bórralas desde una" >&2
    echo "PowerShell como Administrador (en Windows):" >&2
    echo "  takeown /f <carpeta> /r /d S; icacls <carpeta> /grant \"\${env:USERNAME}:(OI)(CI)F\" /t; Remove-Item <carpeta> -Recurse -Force" >&2
    if [ "$(uname -s)" = Linux ]; then
        echo "En Linux/WSL el build falla con estas carpetas. Bórralas, o ejecuta el" >&2
        echo "script desde Git Bash, donde no afectan." >&2
        exit 1
    fi
    note "Advertencia: carpetas ilegibles (no afectan al build desde Windows): ${UNREADABLE[*]}"
else
    echo "Sin problemas de permisos."
fi

# Configuración resuelta (JSON) de todos los proyectos del entorno.
all_configs() {
    local project
    for project in "${PROJECTS[@]}"; do
        compose "$project" config --format json
    done
}

# Un contenedor de cualquier proyecto propio no es conflicto: aunque esté en
# otro proyecto del entorno (p. ej. un microservicio que antes vivía en "sio"),
# lo elimina el "down" de su proyecto actual más adelante.
container_names() {
    grep -oE '"container_name": *"[^"]+"' | sed -E 's/.*"([^"]+)"$/\1/'
}

step "Buscando contenedores con nombres en conflicto"
INFRA_CONTAINERS=" $(compose "$INFRA_PROJECT" config --format json | container_names | tr '\n' ' ') "
CONFLICTS=()
LEGACY=()
while read -r name; do
    [ -n "$name" ] || continue
    owner="$(docker inspect "$name" --format '{{index .Config.Labels "com.docker.compose.project"}}' 2>/dev/null)" || continue
    if [ "$owner" = "$INFRA_PROJECT" ] && [[ "$INFRA_CONTAINERS" != *" $name "* ]]; then
        LEGACY+=("$name")
    elif [[ "$owner" == sio-* ]] && is_own_project "${owner#sio-}"; then
        # Proyecto "sio-<microservicio>" de la versión anterior del entorno.
        LEGACY+=("$name")
    elif ! is_own_project "$owner"; then
        CONFLICTS+=("$name|${owner:-sin proyecto compose}")
    fi
done < <(all_configs | container_names)
if [ "${#LEGACY[@]}" -gt 0 ]; then
    echo "Contenedores de microservicios en proyectos anteriores ('$INFRA_PROJECT' o 'sio-<microservicio>'; se moverán a su proyecto vigente):"
    for name in "${LEGACY[@]}"; do echo "  - $name"; done
fi

if [ "${#CONFLICTS[@]}" -gt 0 ]; then
    echo "Estos contenedores pertenecen a otro proyecto y usan un nombre que este entorno necesita:"
    for item in "${CONFLICTS[@]}"; do
        echo "  - ${item%%|*}  (proyecto: ${item#*|})"
    done
    echo "Se eliminarán solo los contenedores; sus volúmenes se conservan."
    confirm "¿Eliminarlos?" || cancel "no se puede levantar el entorno con esos nombres ocupados."
    for item in "${CONFLICTS[@]}"; do
        docker rm -f "${item%%|*}" >/dev/null
        note "Contenedor en conflicto eliminado: ${item%%|*} (proyecto: ${item#*|})"
    done
else
    echo "Sin conflictos."
fi

# Los puertos salen de infrastructure/.env (docs/port-map.md). Un contenedor de
# otro proyecto que publique uno de ellos impide levantar el entorno: se ofrece
# detenerlo (no se elimina).
PORTS=()
while read -r port; do
    [ -n "$port" ] && PORTS+=("$port")
done < <(all_configs | grep -oE '"published": *"?[0-9]+' | grep -oE '[0-9]+$' | sort -un)

# Variable(s) de .env que definen un puerto, para indicar qué cambiar.
port_vars() {
    grep -E "^[A-Z0-9_]+=$1[[:space:]]*$" "$ENV_FILE" | cut -d= -f1 | paste -sd/ - || true
}

step "Buscando puertos ocupados por otros contenedores"
PORT_HOLDERS=()
while IFS='|' read -r name owner ports; do
    [ -n "$name" ] || continue
    is_own_project "$owner" && continue
    for port in "${PORTS[@]}"; do
        if grep -qE ":${port}->" <<< "$ports"; then
            PORT_HOLDERS+=("$name|${owner:-sin proyecto compose}|$port")
        fi
    done
done < <(docker ps --format '{{.Names}}|{{.Label "com.docker.compose.project"}}|{{.Ports}}')

if [ "${#PORT_HOLDERS[@]}" -gt 0 ]; then
    echo "Estos contenedores de otros proyectos ocupan puertos que este entorno necesita:"
    for item in "${PORT_HOLDERS[@]}"; do
        IFS='|' read -r name owner port <<< "$item"
        echo "  - $name  (proyecto: $owner)  puerto $port  [$(port_vars "$port")]"
    done
    echo "Alternativa: cambiar la variable indicada en $ENV_FILE (y docs/port-map.md)."
    confirm "¿Detenerlos?" || cancel "puertos ocupados."
    for item in "${PORT_HOLDERS[@]}"; do
        IFS='|' read -r name owner port <<< "$item"
        docker stop "$name" >/dev/null 2>&1 || true
        note "Contenedor detenido por ocupar el puerto $port: $name (proyecto: $owner)"
    done
else
    echo "Sin conflictos."
fi

# Indica si algún proceso escucha en el puerto (Linux: ss; Windows/macOS: netstat).
port_in_use() {
    if command -v ss >/dev/null 2>&1; then
        ss -ltnH "sport = :$1" 2>/dev/null | grep -q .
    elif command -v netstat >/dev/null 2>&1; then
        netstat -an 2>/dev/null | grep -iE 'listen' | grep -qE "[:.]$1[[:space:]]"
    else
        return 1
    fi
}

# --- Bajar ------------------------------------------------------------------
# Orden: primero los contenedores heredados de "sio" o "sio-<microservicio>" (si no, retienen los
# volúmenes que el modo completo debe borrar), luego cada microservicio y al
# final "sio", que es dueño de sio-network.
if [ "${#LEGACY[@]}" -gt 0 ]; then
    step "Sacando los microservicios de proyectos anteriores"
    docker rm -f "${LEGACY[@]}" >/dev/null
    note "Contenedores retirados de proyectos anteriores (pasan a su proyecto vigente; volúmenes intactos): ${LEGACY[*]}"
fi

DOWN_ARGS=(--remove-orphans)
if [ "$MODE" = full ]; then
    step "Bajando contenedores y eliminando volúmenes"
    DOWN_ARGS+=(--volumes)
else
    step "Bajando contenedores (se conservan los volúmenes)"
fi
for project in "${PROJECTS[@]:1}" "$INFRA_PROJECT"; do
    echo "--- $project"
    compose "$project" down "${DOWN_ARGS[@]}"
done
if [ "$MODE" = full ]; then
    note "Volúmenes de todos los proyectos eliminados (información anterior borrada)"
else
    note "Volúmenes conservados: la información anterior se mantiene"
fi

# Con el entorno abajo, cualquier puerto aún en escucha es de otro proceso
# (p. ej. un PostgreSQL o RabbitMQ instalado localmente).
step "Verificando que los puertos del entorno estén libres"
BUSY=()
for port in "${PORTS[@]}"; do
    port_in_use "$port" && BUSY+=("$port")
done
if [ "${#BUSY[@]}" -gt 0 ]; then
    echo "Estos puertos están ocupados por otro proceso del host:" >&2
    for port in "${BUSY[@]}"; do
        echo "  - $port  [$(port_vars "$port")]" >&2
    done
    echo "Libera el puerto o cambia la variable en $ENV_FILE (y docs/port-map.md)." >&2
    exit 1
fi
echo "Puertos libres: ${PORTS[*]}"

# --- Construir y levantar -----------------------------------------------------
# Keycloak va primero: todos los microservicios dependen de él para validar
# tokens, así que si falla se detiene aquí antes de construir lo demás.
step "Construyendo Keycloak ${BUILD_ARGS[*]:-}"
compose "$INFRA_PROJECT" build "${BUILD_ARGS[@]}" keycloak

step "Levantando Keycloak y esperando su healthcheck (puede tardar ~1 min)"
compose "$INFRA_PROJECT" up -d --wait keycloak-db keycloak
if [ "$MODE" = full ]; then
    note "Keycloak: realm '${KEYCLOAK_REALM}' reimportado desde la plantilla"
else
    note "Keycloak: realm '${KEYCLOAK_REALM}' conservado (la plantilla no se reaplica)"
fi

step "Construyendo microservicios ${BUILD_ARGS[*]:-}"
for service in "${SERVICES[@]}"; do
    echo "--- $service"
    compose "$(project_of "$service")" build "${BUILD_ARGS[@]}" "$service"
done
note "Imágenes construidas: keycloak ${SERVICES[*]}${BUILD_ARGS[*]:+ (${BUILD_ARGS[*]})}"

step "Levantando el resto de servicios y esperando healthchecks"
for project in "${PROJECTS[@]}"; do
    echo "--- $project"
    compose "$project" up -d --wait
done

# --- Migraciones ----------------------------------------------------------------
# Revisión de Alembic vigente de un servicio ("ninguna" si la base está vacía).
alembic_revision() {
    local rev
    rev="$(compose "$(project_of "$1")" exec -T "$1" alembic current 2>/dev/null | awk 'NF {last = $1} END {print last}')"
    echo "${rev:-ninguna}"
}

step "Aplicando migraciones"
for service in "${SERVICES[@]}"; do
    echo "--- $service"
    before="$(alembic_revision "$service")"
    compose "$(project_of "$service")" exec -T "$service" alembic upgrade head
    after="$(alembic_revision "$service")"
    if [ "$before" = "$after" ]; then
        note "Migraciones $service: sin cambios (revisión $after)"
    else
        note "Migraciones $service: $before -> $after"
    fi
done

# --- Datos iniciales ----------------------------------------------------------
# Ejecuta un seed mostrando su salida y registra su última línea en el resumen.
# Uso: run_seed <etiqueta> <microservicio> <comando...>
run_seed() {
    local label=$1 service=$2 out last
    shift 2
    out="$(mktemp)"
    compose "$(project_of "$service")" exec -T "$service" "$@" | tee "$out"
    last="$(awk 'NF {line = $0} END {print line}' "$out")"
    rm -f "$out"
    note "Datos iniciales $label: cargados${last:+ — $last}"
}

if [ "$MODE" = full ]; then
    step "Datos iniciales: geography-service"
    run_seed geography-service geography-service \
        python -m geography_service.seed load \
        --data-dir /app/services/geography-service/data/south_america

    step "Datos iniciales: product-catalog-service"
    run_seed product-catalog-service product-catalog-service \
        python -m product_catalog_service.seed load

    step "Datos iniciales: payment-reference-service"
    run_seed payment-reference-service payment-reference-service \
        python -m payment_reference_service.seed load

    step "Datos iniciales: party-identity-service (modo país explícito)"
    # El id de Colombia lo genera Geography; se lee de su base para no depender
    # del token técnico de Keycloak.
    COLOMBIA_ID="$(compose "$(project_of geography-service)" exec -T geography-db \
        psql -U "$GEOGRAPHY_DB_USER" -d "$GEOGRAPHY_DB_NAME" -tA \
        -c "SELECT id FROM global_countries WHERE iso2_code = 'CO'" | tr -d '[:space:]')"

    [ -n "$COLOMBIA_ID" ] || { echo "Error: Colombia (CO) no existe en geography-db." >&2; exit 1; }
    echo "Colombia: $COLOMBIA_ID"

    run_seed "party-identity-service (Colombia $COLOMBIA_ID)" party-identity-service \
        python -m party_identity_service.seed load --country-id "$COLOMBIA_ID"

    step "Datos iniciales: party-identity-service (sectores CIIU Rev. 5 A.C.)"
    # Snapshot oficial del DANE incluido en la imagen; no usa red.
    run_seed "party-identity-service (sectores CIIU)" party-identity-service \
        python -m party_identity_service.seed load-business-sectors
else
    skip_step "Datos iniciales (solo en modo completo; la información se conservó)"
fi

# --- Estado final -----------------------------------------------------------
if [ -z "$FINAL_STATE" ]; then
    finish_step OK
    echo
    read -r -p "¿Dejar los contenedores levantados? [Y/n] " answer
    if [[ "$answer" =~ ^[nN]$ ]]; then FINAL_STATE=stop; else FINAL_STATE=up; fi
fi

if [ "$FINAL_STATE" = stop ]; then
    step "Deteniendo contenedores (se conservan contenedores y datos)"
    for project in "${PROJECTS[@]:1}" "$INFRA_PROJECT"; do
        compose "$project" stop
    done
    note "Contenedores detenidos. Para levantarlos: docker compose --file <archivo> --env-file \"$ENV_FILE\" start, empezando por \"$COMPOSE_FILE\" y luego cada $STACKS_DIR/<microservicio>.yaml"
else
    note "Contenedores dejados levantados"
fi
