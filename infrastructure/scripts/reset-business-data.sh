#!/usr/bin/env bash
#
# SIO - Reset de datos funcionales (SOLO entornos no productivos)
#
# Vacía los datos de negocio de ocho microservicios y conserva todo lo demás:
#
#   Se limpia, en este orden (los dependientes antes que aquello a lo que
#   referencian; no hay FK entre bases, pero si el proceso se interrumpe nunca
#   quedan datos apuntando a otros ya borrados):
#     sales -> purchase -> inventory -> commercial-relationship ->
#     operational-context -> product-catalog -> party-identity -> audit
#   (Operational Context referencia identidades de Party Identity; Product
#   Catalog, al fabricante en Party Identity; Audit recibe eventos de todos).
#
#   Se conserva: Geography y Payment Reference (no se tocan), Keycloak y sus
#   usuarios y clientes, bases, esquemas, alembic_version, migraciones y los
#   catálogos maestros de los seeds (unidades de medida, tipos de empaque y
#   tipos de grupo de Product Catalog; sectores CIIU, reglas de identificación
#   y la trazabilidad de la migración 0020 de Party Identity).
#
# Cómo borra: con los servicios, workers y conciliadores detenidos
# (`docker compose stop`, nunca `down`), un `TRUNCATE` por base, en una
# transacción, sobre una lista EXPLÍCITA de tablas y sin CASCADE: si una tabla
# conservada referenciara a una borrada, PostgreSQL rechaza el TRUNCATE y no se
# borra nada de esa base. Antes de borrar compara las tablas reales de cada base
# con las conocidas por este script y se detiene si aparece una nueva (por
# ejemplo, de una migración posterior): hay que clasificarla aquí primero.
#
# Nunca ejecuta `docker compose down -v`, `docker volume rm`, DROP DATABASE ni
# toca Keycloak, Geography o Payment Reference.
#
# Protección contra producción: se niega si `KEYCLOAK_PUBLIC_URL` no apunta a
# la máquina local (localhost / 127.0.0.1 / ::1) o si el entorno define
# `SIO_ENVIRONMENT` con un valor distinto de development/test/local.
#
# Uso (desde cualquier carpeta del repositorio):
#   bash infrastructure/scripts/reset-business-data.sh --dry-run
#   bash infrastructure/scripts/reset-business-data.sh --confirm RESET-SIO-BUSINESS-DATA
#
# Sin --confirm con el texto exacto no borra nada (equivale a --dry-run).
# Después del borrado: reinicia los servicios, ejecuta los seeds idempotentes
# (Product Catalog y Party Identity), comprueba migraciones en head, /health,
# Geography y Payment Reference intactos, maestros conservados y 0 filas en las
# tablas limpiadas. La salida por consola es el único registro (no escribe logs
# ni muestra valores de infrastructure/.env).

set -euo pipefail

CONFIRM_TOKEN="RESET-SIO-BUSINESS-DATA"
HEALTH_TIMEOUT_SECONDS=180

# --- Raíz del repositorio y configuración -------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || (cd "$SCRIPT_DIR/../.." && pwd))"
INFRA_DIR="$ROOT_DIR/infrastructure"
ENV_FILE="$INFRA_DIR/.env"
STACKS_DIR="$INFRA_DIR/services"

usage() {
    sed -n '2,/^set -euo pipefail/p' "${BASH_SOURCE[0]}" | sed -e '/^set -euo/d' -e 's/^# \{0,1\}//'
}

MODE=dry-run
while [ $# -gt 0 ]; do
    case "$1" in
        --dry-run) MODE=dry-run ;;
        --confirm)
            [ $# -ge 2 ] || { echo "Error: --confirm necesita el texto $CONFIRM_TOKEN." >&2; exit 2; }
            if [ "$2" != "$CONFIRM_TOKEN" ]; then
                echo "Error: texto de confirmación incorrecto; no se borra nada." >&2
                exit 2
            fi
            MODE=execute
            shift
            ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Error: opción desconocida '$1' (use --dry-run o --confirm $CONFIRM_TOKEN)." >&2; exit 2 ;;
    esac
    shift
done

[ -f "$ENV_FILE" ] || { echo "Error: no existe $ENV_FILE (cp infrastructure/.env.example infrastructure/.env)." >&2; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "Error: docker no está disponible." >&2; exit 1; }

# shellcheck disable=SC1090
set -a; . "$ENV_FILE"; set +a
unset COMPOSE_PROJECT_NAME

compose() {
    local project=$1
    shift
    docker compose --project-name "$project" --file "$STACKS_DIR/$project.yaml" --env-file "$ENV_FILE" "$@"
}

# --- Plan: servicios, bases y tablas --------------------------------------------
# Orden de limpieza (ver cabecera).
SERVICES=(
    sales-service
    purchase-service
    inventory-service
    commercial-relationship-service
    operational-context-service
    product-catalog-service
    party-identity-service
    audit-service
)
PRESERVED_SERVICES=(geography-service payment-reference-service)

declare -A DB_OF=(
    [sales-service]=sales-db
    [purchase-service]=purchase-db
    [inventory-service]=inventory-db
    [commercial-relationship-service]=commercial-relationship-db
    [operational-context-service]=operational-context-db
    [product-catalog-service]=product-catalog-db
    [party-identity-service]=party-identity-db
    [audit-service]=audit-db
    [geography-service]=geography-db
    [payment-reference-service]=payment-reference-db
)

# Tablas que se vacían (datos de negocio y su outbox de auditoría).
declare -A WIPE=(
    [sales-service]="sales sale_details sale_operations sale_sequences sale_sequence_counters audit_outbox"
    [purchase-service]="purchases purchase_details purchase_operations purchase_lifecycle_events purchase_sequences purchase_sequence_counters audit_outbox"
    [inventory-service]="inventory_operations inventory_movements inventory_balances inventory_cost_layers inventory_cost_consumptions inventory_adjustments inventory_counts inventory_count_details inventory_policies company_inventory_policies audit_outbox"
    [commercial-relationship-service]="company_products company_product_presentations company_customers company_suppliers supplier_products supplier_payment_conditions price_lists price_list_items audit_outbox"
    [operational-context-service]="companies branches application_users user_branches company_advisor_assignments audit_outbox"
    [product-catalog-service]="global_products global_product_presentations global_product_identifiers global_product_categories global_product_group_assignments global_product_attribute_values product_assets global_brands global_categories global_category_attributes global_product_groups product_attribute_definitions product_attribute_options audit_outbox"
    [party-identity-service]="person_identities organization_identities person_contact_profiles organization_contact_profiles organization_contact_persons organization_legal_representatives organization_business_sectors audit_outbox"
    [audit-service]="audit_events"
)

# Tablas que se conservan en esos mismos servicios (además de alembic_version).
declare -A KEEP=(
    [sales-service]=""
    [purchase-service]=""
    [inventory-service]=""
    [commercial-relationship-service]=""
    [operational-context-service]=""
    [product-catalog-service]="global_units_of_measure global_packaging_types global_product_group_types"
    [party-identity-service]="global_business_sectors identification_type_rules identification_type_rule_country_corrections"
    [audit-service]=""
)

# Comandos de seed idempotentes que se ejecutan tras el borrado (servicio|comando).
SEEDS=(
    "product-catalog-service|python -m product_catalog_service.seed load"
    "party-identity-service|python -m party_identity_service.seed load"
    "party-identity-service|python -m party_identity_service.seed load-business-sectors"
)

# --- Utilidades ----------------------------------------------------------------
step() { printf '\n==> %s\n' "$*"; }
note() { printf '    %s\n' "$*"; }
fail() { printf '\nError: %s\n' "$*" >&2; exit 1; }

# psql dentro del contenedor de la base: usa las variables del propio contenedor,
# así que ningún usuario ni contraseña pasa por esta terminal.
psql_db() {
    local service=$1 sql=$2
    compose "$service" exec -T "${DB_OF[$service]}" sh -c \
        'psql -X -q -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tA -c "$0"' "$sql"
}

table_list() {
    psql_db "$1" "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY 1" | tr -d '\r'
}

row_count() {
    psql_db "$1" "SELECT count(*) FROM \"$2\"" | tr -d '[:space:]'
}

app_services() {
    # Contenedores del proyecto que no son bases: API, workers y conciliadores.
    compose "$1" config --services | grep -v -E -- '-db$' || true
}

container_state() {
    # running|healthy, running|, exited|, ... del contenedor de un servicio compose.
    compose "$1" ps -a --format '{{.Service}}|{{.State}}|{{.Health}}' 2>/dev/null \
        | awk -F'|' -v s="$2" '$1 == s { print $2 "|" $3 }'
}

alembic_current() {
    compose "$1" exec -T "$1" alembic current 2>/dev/null | awk 'NF { print $1 }' | tail -1
}

alembic_heads() {
    compose "$1" exec -T "$1" alembic heads 2>/dev/null | awk 'NF { print $1 }' | tail -1
}

wait_healthy() {
    local service=$1 deadline=$((SECONDS + HEALTH_TIMEOUT_SECONDS)) state
    while [ $SECONDS -lt $deadline ]; do
        state="$(container_state "$service" "$service")"
        [ "$state" = "running|healthy" ] && return 0
        sleep 3
    done
    return 1
}

http_status_inside() {
    compose "$1" exec -T "$1" python -c \
        "import sys, urllib.request
try:
    print(urllib.request.urlopen('http://localhost:8000$2', timeout=10).status)
except Exception as error:
    print(getattr(error, 'code', 0))" 2>/dev/null | tr -d '[:space:]'
}

# --- Protección contra producción ------------------------------------------------
guard_non_production() {
    local url="${KEYCLOAK_PUBLIC_URL:-}" host
    if [ -n "${SIO_ENVIRONMENT:-}" ] && ! [[ "$SIO_ENVIRONMENT" =~ ^(development|test|local)$ ]]; then
        fail "SIO_ENVIRONMENT='$SIO_ENVIRONMENT': este script solo se ejecuta en entornos de desarrollo o pruebas."
    fi
    host="$(sed -E 's#^[a-zA-Z]+://##; s#[/:].*$##; s#^\[##; s#\]$##' <<< "$url")"
    case "$host" in
        localhost|127.0.0.1|::1) ;;
        *) fail "KEYCLOAK_PUBLIC_URL no apunta a la máquina local ('$host'); se asume un entorno no desarrollo y no se borra nada." ;;
    esac
}

# --- 1. Verificaciones previas (no modifican nada) ---------------------------------
declare -A BEFORE_COUNT=()
declare -A BEFORE_REVISION=()

preflight() {
    step "Verificaciones previas (solo lectura)"
    guard_non_production
    note "Repositorio: $ROOT_DIR"
    note "Entorno local verificado (KEYCLOAK_PUBLIC_URL en la máquina local)."

    local service db state known actual table unknown missing revision head
    for service in "${SERVICES[@]}" "${PRESERVED_SERVICES[@]}"; do
        db="${DB_OF[$service]}"
        state="$(container_state "$service" "$db")"
        [ "$state" = "running|healthy" ] || fail "la base $db no está en ejecución y saludable ($state)."
        state="$(container_state "$service" "$service")"
        [ "$state" = "running|healthy" ] || fail "el servicio $service no está en ejecución y saludable ($state)."
    done
    note "Bases y servicios en ejecución y saludables (10)."

    for service in "${SERVICES[@]}"; do
        known=" alembic_version ${WIPE[$service]} ${KEEP[$service]} "
        actual="$(table_list "$service")"
        unknown=""
        for table in $actual; do
            [[ "$known" == *" $table "* ]] || unknown+=" $table"
        done
        [ -z "$unknown" ] || fail "$service tiene tablas que este script no clasifica:$unknown. Clasifíquelas (borrar/conservar) antes de continuar."
        missing=""
        for table in ${WIPE[$service]} ${KEEP[$service]}; do
            grep -qx "$table" <<< "$actual" || missing+=" $table"
        done
        [ -z "$missing" ] || fail "$service no tiene las tablas esperadas:$missing (¿migraciones pendientes?)."

        revision="$(alembic_current "$service")"
        head="$(alembic_heads "$service")"
        [ -n "$revision" ] && [ "$revision" = "$head" ] || fail "$service no está en head (actual '$revision', head '$head')."
        BEFORE_REVISION[$service]="$revision"
    done
    note "Tablas reconocidas y migraciones en head en los 8 servicios."

    for service in "${PRESERVED_SERVICES[@]}"; do
        revision="$(alembic_current "$service")"
        BEFORE_REVISION[$service]="$revision"
    done

    printf '\n    %-34s %-48s %10s  %s\n' "Servicio" "Tabla" "Filas" "Acción"
    printf '    %-34s %-48s %10s  %s\n' "--------" "-----" "-----" "------"
    for service in "${SERVICES[@]}"; do
        for table in ${WIPE[$service]}; do
            BEFORE_COUNT["$service.$table"]="$(row_count "$service" "$table")"
            printf '    %-34s %-48s %10s  %s\n' "$service" "$table" "${BEFORE_COUNT[$service.$table]}" "BORRAR"
        done
        for table in alembic_version ${KEEP[$service]}; do
            BEFORE_COUNT["$service.$table"]="$(row_count "$service" "$table")"
            printf '    %-34s %-48s %10s  %s\n' "$service" "$table" "${BEFORE_COUNT[$service.$table]}" "conservar"
        done
    done
    for service in "${PRESERVED_SERVICES[@]}"; do
        for table in $(table_list "$service"); do
            BEFORE_COUNT["$service.$table"]="$(row_count "$service" "$table")"
            printf '    %-34s %-48s %10s  %s\n' "$service" "$table" "${BEFORE_COUNT[$service.$table]}" "no se toca"
        done
    done
}

# --- 2. Borrado -----------------------------------------------------------------------
STOPPED_PROJECTS=()

restart_stopped() {
    local service
    for service in "${STOPPED_PROJECTS[@]}"; do
        # shellcheck disable=SC2046
        compose "$service" start $(app_services "$service") >/dev/null 2>&1 || true
    done
}

on_error() {
    local code=$?
    echo >&2
    echo "El reset se detuvo con error (código $code). Bases ya limpiadas: ${CLEANED[*]:-ninguna}." >&2
    echo "Se intenta volver a iniciar los servicios detenidos; revise su estado con docker ps." >&2
    restart_stopped
    exit "$code"
}

CLEANED=()

execute_reset() {
    trap on_error ERR

    local service services tables
    step "Deteniendo APIs, workers y conciliadores (docker compose stop; las bases siguen en ejecución)"
    for service in "${SERVICES[@]}"; do
        services="$(app_services "$service" | tr '\n' ' ')"
        # shellcheck disable=SC2086
        compose "$service" stop $services >/dev/null 2>&1
        STOPPED_PROJECTS+=("$service")
        note "$service: detenidos $services"
    done

    step "Vaciando tablas de negocio (TRUNCATE explícito, una transacción por base, sin CASCADE)"
    for service in "${SERVICES[@]}"; do
        tables="$(sed -E 's/ +/, /g; s/^, //; s/, $//' <<< "${WIPE[$service]}")"
        psql_db "$service" "BEGIN; TRUNCATE TABLE $tables; COMMIT;" >/dev/null
        CLEANED+=("$service")
        note "$service: $(wc -w <<< "${WIPE[$service]}") tablas vaciadas"
    done

    step "Iniciando servicios"
    restart_stopped
    for service in "${SERVICES[@]}"; do
        wait_healthy "$service" || fail "$service no quedó saludable en ${HEALTH_TIMEOUT_SECONDS}s."
        note "$service: saludable"
    done
    STOPPED_PROJECTS=()

    step "Seeds idempotentes"
    local entry command
    for entry in "${SEEDS[@]}"; do
        service="${entry%%|*}"
        command="${entry#*|}"
        note "$service: $command"
        # shellcheck disable=SC2086
        compose "$service" exec -T "$service" $command 2>&1 | sed 's/^/        /'
    done
    trap - ERR
}

# --- 3. Validaciones posteriores ------------------------------------------------------
FAILURES=0
check() {
    if [ "$2" = ok ]; then
        printf '    OK     %s\n' "$1"
    else
        printf '    FALLA  %s\n' "$1"
        FAILURES=$((FAILURES + 1))
    fi
}

validate() {
    step "Validaciones posteriores"
    local service table count revision status bad workers
    for service in "${SERVICES[@]}" "${PRESERVED_SERVICES[@]}"; do
        revision="$(alembic_current "$service")"
        [ "$revision" = "${BEFORE_REVISION[$service]}" ] && check "$service: migración $revision (sin cambios, head)" ok \
            || check "$service: migración '$revision' distinta de '${BEFORE_REVISION[$service]}'" fail
        for path in /health/live /health/ready; do
            status="$(http_status_inside "$service" "$path")"
            [ "$status" = 200 ] && check "$service: $path 200" ok || check "$service: $path $status" fail
        done
    done

    for service in "${SERVICES[@]}"; do
        bad=""
        for table in ${WIPE[$service]}; do
            count="$(row_count "$service" "$table")"
            [ "$count" = 0 ] || bad+=" $table=$count"
        done
        [ -z "$bad" ] && check "$service: 0 filas en las $(wc -w <<< "${WIPE[$service]}") tablas limpiadas" ok \
            || check "$service: quedan filas:$bad" fail
        for table in ${KEEP[$service]}; do
            count="$(row_count "$service" "$table")"
            [ "$count" = "${BEFORE_COUNT[$service.$table]}" ] && check "$service: $table conservada ($count filas)" ok \
                || check "$service: $table cambió (${BEFORE_COUNT[$service.$table]} -> $count)" fail
        done
        workers="$(app_services "$service" | grep -v -x "$service" | tr '\n' ' ')"
        for worker in $workers; do
            [[ "$(container_state "$service" "$worker")" == running* ]] && check "$service: $worker en ejecución" ok \
                || check "$service: $worker no está en ejecución" fail
        done
    done

    for service in "${PRESERVED_SERVICES[@]}"; do
        for table in $(table_list "$service"); do
            count="$(row_count "$service" "$table")"
            [ "$count" = "${BEFORE_COUNT[$service.$table]}" ] && [ "$count" != 0 -o "$table" = alembic_version ] \
                && check "$service: $table poblada e intacta ($count filas)" ok \
                || check "$service: $table ${BEFORE_COUNT[$service.$table]} -> $count" fail
        done
    done
}

# --- Ejecución ----------------------------------------------------------------------------
echo "SIO - Reset de datos funcionales ($( [ "$MODE" = execute ] && echo 'EJECUCIÓN' || echo 'simulación: --dry-run' ))"
preflight

if [ "$MODE" != execute ]; then
    step "Simulación terminada: no se modificó nada"
    note "Para ejecutar el borrado:"
    note "  bash infrastructure/scripts/reset-business-data.sh --confirm $CONFIRM_TOKEN"
    exit 0
fi

START=$SECONDS
execute_reset
validate

step "Resumen"
note "Servicios limpiados (en orden): ${CLEANED[*]}"
note "Conservados: Geography, Payment Reference, Keycloak, maestros de los seeds, migraciones."
note "Duración: $((SECONDS - START)) s"
if [ "$FAILURES" -eq 0 ]; then
    note "Resultado: entorno sin datos de negocio y listo para una importación."
else
    note "Resultado: $FAILURES validaciones fallidas (ver arriba)."
    exit 1
fi
