#!/usr/bin/env bash
# Comando único de la validación integral del MVP (017).
# Contrato: specs/017-mvp-integral-validation/contracts/runner-cli.md
#
# Uso (desde la raíz del repositorio):
#   bash validation/mvp-e2e/run.sh [--todo] [--etapa X ...] [--linea-base] [--restaurar] [--sin-caidas]
#
# Crea validation/mvp-e2e/.venv si falta (dependencias de pyproject.toml) y llama a run.py con los
# mismos argumentos. No imprime variables de entorno ni secretos.
set -euo pipefail

SUITE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SUITE_DIR/.venv"
STAMP="$VENV_DIR/.sio-mvp-installed"

venv_python() {
    if [ -x "$VENV_DIR/bin/python" ]; then
        echo "$VENV_DIR/bin/python"
    elif [ -x "$VENV_DIR/Scripts/python.exe" ]; then
        echo "$VENV_DIR/Scripts/python.exe"
    fi
}

# Primer intérprete >= 3.12 disponible (SIO_MVP_PYTHON lo fija explícitamente).
find_python() {
    local candidate
    for candidate in ${SIO_MVP_PYTHON:-} python3.13 python3.12 python3 python py; do
        command -v "$candidate" >/dev/null 2>&1 || continue
        if "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)' 2>/dev/null; then
            echo "$candidate"
            return 0
        fi
    done
    return 1
}

dependencies() {
    "$1" -c 'import sys, tomllib
with open(sys.argv[1], "rb") as handle:
    print("\n".join(tomllib.load(handle)["project"]["dependencies"]))' "$SUITE_DIR/pyproject.toml"
}

create_venv() {
    local base
    base="$(find_python)" || {
        echo "Error: se necesita Python >= 3.12 (o SIO_MVP_PYTHON apuntando a uno)." >&2
        exit 2
    }
    echo "==> Creando $VENV_DIR con $base" >&2
    if ! "$base" -m venv "$VENV_DIR" >/dev/null 2>&1; then
        rm -rf "$VENV_DIR"
        # Algunos Python de distribución no traen ensurepip; uv crea el entorno sin él.
        command -v uv >/dev/null 2>&1 || {
            echo "Error: '$base -m venv' falló y uv no está disponible." >&2
            exit 2
        }
        uv venv --quiet --python "$base" "$VENV_DIR"
    fi
}

install_dependencies() {
    local python deps
    python="$(venv_python)"
    mapfile -t deps < <(dependencies "$python")
    echo "==> Instalando dependencias de la suite" >&2
    if "$python" -m pip --version >/dev/null 2>&1; then
        "$python" -m pip install --quiet "${deps[@]}"
    else
        uv pip install --quiet --python "$python" "${deps[@]}"
    fi
    touch "$STAMP"
}

[ -n "$(venv_python)" ] || create_venv
if [ ! -f "$STAMP" ] || [ "$SUITE_DIR/pyproject.toml" -nt "$STAMP" ]; then
    install_dependencies
fi

exec "$(venv_python)" "$SUITE_DIR/run.py" "$@"
