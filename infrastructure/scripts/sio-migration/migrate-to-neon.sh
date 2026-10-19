#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'USAGE'
Uso (desde la raíz del repositorio):
  bash infrastructure/scripts/sio-migration/migrate-to-neon.sh --service geography --dry-run
  CONFIRM_MIGRATION=YES bash infrastructure/scripts/sio-migration/migrate-to-neon.sh --service geography --execute
  bash infrastructure/scripts/sio-migration/migrate-to-neon.sh --all --dry-run

Configuración: NEON_ENV_FILE (por defecto junto al script: neon-migration.env)
Requiere: Docker y Python 3. El usuario Neon debe poder crear bases de datos.
La URL única NEON_BASE_URL puede apuntar a neondb: el script cambia solo el nombre de la base.
En --all omite bases ya migradas, crea las faltantes y restaura solo en destinos vacíos.
--dry-run NO crea bases ni escribe datos.
USAGE
}
MODE=''; TARGET=''; ALL=0
while (($#)); do
  case "$1" in
    --dry-run) MODE=dry-run ;;
    --execute) MODE=execute ;;
    --service) shift; TARGET="${1:-}" ;;
    --all) ALL=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Argumento desconocido: $1" >&2; usage; exit 2 ;;
  esac
  shift
done
[[ -n "$MODE" && $((ALL + (${#TARGET} > 0))) -eq 1 ]] || { usage; exit 2; }
command -v docker >/dev/null || { echo 'Docker no instalado' >&2; exit 1; }
command -v python3 >/dev/null || { echo 'Falta python3' >&2; exit 1; }
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NEON_ENV_FILE="${NEON_ENV_FILE:-$SCRIPT_DIR/neon-migration.env}"
[[ -f "$NEON_ENV_FILE" ]] || { echo "No existe $NEON_ENV_FILE" >&2; exit 1; }
set -a
# shellcheck disable=SC1090
source "$NEON_ENV_FILE"
set +a
[[ -n "${NEON_BASE_URL:-}" ]] || { echo 'Falta NEON_BASE_URL en el archivo de configuración' >&2; exit 1; }
BACKUP_DIR="${BACKUP_DIR:-./backups/neon-migration}"
mkdir -p "$BACKUP_DIR"
BACKUP_DIR="$(cd "$BACKUP_DIR" && pwd)"
chmod 700 "$BACKUP_DIR"
SERVICES=(geography party-identity product-catalog operational-context payment-reference commercial-relationship purchase sales inventory audit workflow)

make_target_url() {
  TARGET_DB="$1" python3 - <<'PY'
import os, sys
from urllib.parse import urlsplit, urlunsplit, quote, parse_qs
url=os.environ['NEON_BASE_URL']
try:
    u=urlsplit(url)
    if u.scheme not in ('postgresql', 'postgres') or not u.hostname or not u.username:
        raise ValueError('URL PostgreSQL incompleta')
    if parse_qs(u.query).get('sslmode', [''])[0] not in ('require', 'verify-full'):
        raise ValueError('NEON_BASE_URL debe contener sslmode=require o verify-full')
    db=os.environ['TARGET_DB']
    print(urlunsplit((u.scheme,u.netloc,'/'+quote(db,safe=''),u.query,u.fragment)))
except ValueError as e:
    print('NEON_BASE_URL no válida: '+str(e), file=sys.stderr)
    sys.exit(1)
PY
}

# Ejecuta psql y createdb desde contenedores temporales de PostgreSQL 18.
# La URL se pasa como variable de entorno, nunca como argumento shell del host.
remote_psql() {
  docker run --rm --network host -i -e PGURL="$NEON_BASE_URL" \
    postgres:18-bookworm sh -ec 'exec psql "$PGURL" -X -qAt -v ON_ERROR_STOP=1 -f -'
}

remote_database_exists() {
  local db="$1" answer
  # El nombre es generado a partir de la lista fija SERVICES (solo letras y _).
  answer="$(printf "SELECT count(*) FROM pg_database WHERE datname = '%s';\n" "$db" | remote_psql)" || return 2
  case "$answer" in
    0) return 1 ;; 1) return 0 ;;
    *) echo "Consulta inesperada del catálogo para $db: $answer" >&2; return 2 ;;
  esac
}

create_remote_database() {
  local db="$1"
  docker run --rm --network host -e PGURL="$NEON_BASE_URL" -e DBNAME="$db" \
    postgres:18-bookworm sh -ec 'exec createdb --maintenance-db="$PGURL" "$DBNAME"'
}

remote_objects_count() {
  local url="$1"
  docker run --rm --network host -i -e TARGET_URL="$url" postgres:18-bookworm \
    sh -ec 'exec psql "$TARGET_URL" -X -qAt -v ON_ERROR_STOP=1 -f -' <<'SQL'
SELECT
  (SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
   WHERE n.nspname NOT IN ('pg_catalog','information_schema')
     AND n.nspname NOT LIKE 'pg_toast%' AND n.nspname NOT LIKE 'pg_temp%')
+ (SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
   WHERE n.nspname NOT IN ('pg_catalog','information_schema'))
+ (SELECT count(*) FROM pg_type t JOIN pg_namespace n ON n.oid=t.typnamespace
   WHERE n.nspname NOT IN ('pg_catalog','information_schema')
     AND t.typtype IN ('e','d'));
SQL
}

run_one() {
  local svc="$1"
  local db_container="sio-${svc}-db"
  local target_db="sio_${svc//-/_}_dev"
  local url db_name file count exists_status
  url="$(make_target_url "$target_db")" || return 1
  docker inspect "$db_container" >/dev/null 2>&1 || { echo "No existe $db_container" >&2; return 1; }
  [[ "$(docker inspect -f '{{.State.Running}}' "$db_container")" == true ]] || { echo "$db_container no está activo" >&2; return 1; }
  db_name="$(docker exec "$db_container" sh -c 'printf %s "${POSTGRES_DB:-${POSTGRES_USER:-postgres}}"')"
  file="$BACKUP_DIR/${svc}-$(date +%Y%m%d-%H%M%S).dump"
  echo "[$svc] Origen: $db_container / $db_name; destino Neon: $target_db"

  exists_status=0
  remote_database_exists "$target_db" || exists_status=$?
  if ((exists_status == 2)); then
    echo "[$svc] ERROR: no fue posible consultar las bases disponibles en Neon." >&2
    return 1
  fi
  if ((exists_status == 1)); then
    if [[ "$MODE" == dry-run ]]; then
      echo "[$svc] DRY-RUN: se CREARÍA $target_db y luego se migraría (sin cambios realizados)."
      return 0
    fi
    [[ "${CONFIRM_MIGRATION:-}" == YES ]] || { echo 'Para ejecutar establece CONFIRM_MIGRATION=YES' >&2; return 1; }
    echo "[$svc] Creando base $target_db en Neon..."
    if ! create_remote_database "$target_db"; then
      echo "[$svc] ERROR al crear $target_db. Verifica permisos CREATE DATABASE del usuario Neon." >&2
      return 1
    fi
  fi

  count="$(remote_objects_count "$url")" || { echo "[$svc] ERROR: no se pudo comprobar el contenido de $target_db." >&2; return 1; }
  [[ "$count" =~ ^[0-9]+$ ]] || { echo "[$svc] Conteo de objetos inválido: $count" >&2; return 1; }
  if ((count > 0)); then
    if ((ALL)); then
      echo "[$svc] OMITIDO: $target_db ya contiene $count objetos; no se sobrescribe. Verificar manualmente si está completa."
      return 0
    fi
    echo "[$svc] BLOQUEADO: $target_db contiene $count objetos; no se sobrescribe." >&2
    return 1
  fi
  if [[ "$MODE" == dry-run ]]; then
    echo "[$svc] DRY-RUN OK: $target_db está vacía; migración pendiente, sin cambios."
    return 0
  fi
  [[ "${CONFIRM_MIGRATION:-}" == YES ]] || { echo 'Para ejecutar establece CONFIRM_MIGRATION=YES' >&2; return 1; }
  echo "[$svc] Creando respaldo: $file"
  if ! docker exec "$db_container" sh -ec 'exec pg_dump -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-${POSTGRES_USER:-postgres}}" -Fc --no-owner --no-acl' > "$file"; then
    rm -f "$file"; echo "[$svc] Error en pg_dump" >&2; return 1
  fi
  chmod 600 "$file"
  if ! docker run --rm -v "$BACKUP_DIR:/backup:ro" postgres:18-bookworm \
     pg_restore --list "/backup/$(basename "$file")" >/dev/null; then
     echo "[$svc] Respaldo inválido: $file" >&2; return 1
  fi
  # Si falla la restauración la DB creada se conserva para inspección;
  # las restauraciones son atómicas gracias a --single-transaction.
  echo "[$svc] Respaldo validado; restaurando en Neon..."
  docker run --rm --network host -v "$BACKUP_DIR:/backup:ro" -e TARGET_URL="$url" \
    -e DUMP_FILE="/backup/$(basename "$file")" postgres:18-bookworm \
    sh -ec 'exec pg_restore --dbname="$TARGET_URL" --no-owner --no-acl --exit-on-error --single-transaction "$DUMP_FILE"'
  echo "[$svc] Restauración completada. Verifica conteos contra origen antes de desplegar."
}

if ((ALL)); then
  failures=0
  for svc in "${SERVICES[@]}"; do
    if docker inspect "sio-${svc}-db" >/dev/null 2>&1; then
      run_one "$svc" || failures=$((failures+1))
    fi
  done
  ((failures==0)) || { echo "$failures servicios fallaron o fueron bloqueados" >&2; exit 1; }
else
  case " ${SERVICES[*]} " in *" $TARGET "*) ;; *) echo "Servicio no admitido: $TARGET" >&2; exit 2 ;; esac
  run_one "$TARGET"
fi
