#!/usr/bin/env bash
#
# Pruebas de infrastructure/scripts/reset-business-data.sh que no borran nada.
#
#   bash infrastructure/scripts/tests/reset-business-data.test.sh          # estáticas
#   bash infrastructure/scripts/tests/reset-business-data.test.sh --live   # + --dry-run real
#
# Con --live exige el entorno levantado y comprueba que el --dry-run no cambia
# ningún conteo de filas.

set -uo pipefail

TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="$TEST_DIR/../reset-business-data.sh"
FAILURES=0

pass() { printf 'OK     %s\n' "$1"; }
failed() { printf 'FALLA  %s\n' "$1"; FAILURES=$((FAILURES + 1)); }
expect() { if eval "$2"; then pass "$1"; else failed "$1"; fi; }

# Solo las líneas ejecutables (sin comentarios), para que la cabecera pueda
# nombrar lo que el script nunca hace.
CODE="$(grep -v -E '^\s*#' "$SCRIPT")"

expect "sintaxis bash válida" 'bash -n "$SCRIPT"'
expect "sin 'down' de compose" '! grep -qE "compose[^|]*\bdown\b" <<< "$CODE"'
expect "sin 'docker volume rm'" '! grep -qE "volume +rm" <<< "$CODE"'
expect "sin borrado de volúmenes (compose stop/rm con -v o --volumes)" '! grep -qE "compose[^|]*\b(stop|rm|down)\b[^|]*(\s-v\b|--volumes)" <<< "$CODE"'
expect "sin DROP" '! grep -qiE "\bdrop\b" <<< "$CODE"'
expect "TRUNCATE sin CASCADE" 'grep -q "psql_db.*TRUNCATE TABLE" <<< "$CODE" && ! grep -E "psql_db.*TRUNCATE" <<< "$CODE" | grep -qi cascade'
expect "no toca Keycloak" '! grep -qiE "keycloak-db|compose \"?sio\"? |realms/.*/users" <<< "$CODE"'
expect "Geography y Payment Reference sin tablas que borrar" '! grep -qE "\[(geography|payment-reference)-service\]=\"[a-z]" <<< "$(sed -n "/declare -A WIPE/,/^)/p" "$SCRIPT")"'
expect "sin rutas personales" '! grep -qE "/home/|/Users/|C:\\\\" "$SCRIPT"'
expect "sin contraseñas ni secretos en el código" '! grep -qiE "(password|secret)=[^\$\"]" "$SCRIPT"'
expect "alembic_version nunca en la lista de borrado" '! sed -n "/declare -A WIPE/,/^)/p" "$SCRIPT" | grep -q alembic_version'

out="$(bash "$SCRIPT" --confirm OTRO-TEXTO 2>&1)"; rc=$?
expect "texto de confirmación incorrecto: código 2 y no borra" '[ $rc -eq 2 ] && grep -q "no se borra nada" <<< "$out"'
out="$(bash "$SCRIPT" --opcion-inexistente 2>&1)"; rc=$?
expect "opción desconocida: código 2" '[ $rc -eq 2 ]'
out="$(bash "$SCRIPT" --help 2>&1)"; rc=$?
expect "--help muestra el uso" '[ $rc -eq 0 ] && grep -q -- "--dry-run" <<< "$out"'

out="$(env SIO_ENVIRONMENT=production bash "$SCRIPT" --dry-run 2>&1)"; rc=$?
expect "SIO_ENVIRONMENT=production: se niega" '[ $rc -ne 0 ] && grep -q "solo se ejecuta en entornos de desarrollo" <<< "$out"'

if [ "${1:-}" = --live ]; then
    snapshot() {
        local c
        for c in $(docker ps --format '{{.Names}}' | grep -E '^sio-.*-db$' | grep -v -E 'keycloak|test|workflow'); do
            docker exec "$c" sh -c 'psql -X -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tA -F" " -c "SELECT relname, n_tup_ins, n_tup_del FROM pg_stat_user_tables ORDER BY relname"' 2>/dev/null \
                | sed "s/^/$c /"
        done
    }
    before="$(snapshot)"
    out="$(bash "$SCRIPT" --dry-run 2>&1)"; rc=$?
    after="$(snapshot)"
    expect "--dry-run real termina sin error" '[ $rc -eq 0 ] && grep -q "no se modificó nada" <<< "$out"'
    expect "--dry-run real no inserta ni borra filas" '[ "$before" = "$after" ]'
fi

echo
[ "$FAILURES" -eq 0 ] && echo "Resultado: todas las pruebas pasaron." || { echo "Resultado: $FAILURES fallidas."; exit 1; }
