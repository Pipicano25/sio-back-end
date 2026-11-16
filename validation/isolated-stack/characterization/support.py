"""Apoyo de la caracterización extremo a extremo de la spec 025 (T011).

La red de seguridad es: grabar cada caso con las lecturas por HTTP (el código de hoy) y reproducirlo con las
lecturas por contrato. Un caso guarda el estado, el cuerpo normalizado, los efectos y las solicitudes internas.

- ``SIO_CHARACTERIZATION_RECORD=1`` graba en ``cases/<módulo>.json``; sin la variable, compara con lo grabado.
- Los identificadores, las fechas y las trazas se normalizan, de modo que dos ejecuciones con datos nuevos son
  comparables. Cada UUID se reemplaza por su alias (si el mundo lo registró) o por ``<id:N>`` en orden de aparición.
- Las solicitudes internas se cuentan en los registros de acceso de los contenedores ``sio-it-*``
  (``docker logs --since/--until``), sin leer cuerpos ni cabeceras.

Nada de este módulo imprime tokens ni secretos.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
CASES_DIR = HERE / "cases"
RECORD = os.environ.get("SIO_CHARACTERIZATION_RECORD", "").strip() == "1"

UUID_RE = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.IGNORECASE)
TS_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?\b")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
VOLATILE_KEYS = frozenset({"trace_id", "request_id", "correlation_id", "traceparent"})
ACCESS_LINE = re.compile(r'"(?P<method>GET|POST|PUT|PATCH|DELETE) (?P<path>[^ ?"]+)(?:\?[^ "]*)? HTTP/[\d.]+" (?P<status>\d{3})')


# --------------------------------------------------------------------------- normalización


class Normalizer:
    """Reemplaza valores volátiles por marcadores estables dentro de un caso."""

    def __init__(self, aliases: Mapping[str, str] | None = None, run: str | None = None) -> None:
        self._aliases = {key.lower(): value for key, value in (aliases or {}).items()}
        self._seen: dict[str, str] = {}
        self._run = run

    def _uuid(self, value: str) -> str:
        key = value.lower()
        if key in self._aliases:
            return f"<{self._aliases[key]}>"
        if key not in self._seen:
            self._seen[key] = f"<id:{len(self._seen) + 1}>"
        return self._seen[key]

    def text(self, value: str) -> str:
        value = UUID_RE.sub(lambda match: self._uuid(match.group(0)), value)
        value = TS_RE.sub("<ts>", value)
        if self._run:
            value = value.replace(self._run, "<run>")
        return value

    def __call__(self, value: Any, key: str | None = None) -> Any:
        if key is not None and key.lower() in VOLATILE_KEYS:
            return "<volátil>"
        if isinstance(value, Mapping):
            return {name: self(item, name) for name, item in sorted(value.items())}
        if isinstance(value, list):
            return [self(item) for item in value]
        if isinstance(value, str):
            if key is not None and key.endswith(("_at", "_date")) and (TS_RE.fullmatch(value) or DATE_RE.match(value)):
                return "<fecha>"
            return self.text(value)
        return value


def response_case(response, normalizer: Normalizer) -> dict[str, Any]:
    """Estado y cuerpo normalizado de una respuesta ``httpx``."""
    try:
        body: Any = response.json() if response.content else None
    except ValueError:
        body = {"texto": normalizer.text(response.text[:2000])}
    return {"status": response.status_code, "body": normalizer(body)}


# --------------------------------------------------------------------------- solicitudes internas


def _docker(args: list[str]) -> str:
    completed = subprocess.run(["docker", *args], capture_output=True, text=True, timeout=60, check=False)
    # Los registros de acceso de uvicorn van a stderr.
    return completed.stdout + completed.stderr


def _rfc3339(moment: float) -> str:
    return datetime.fromtimestamp(moment, UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def normalize_path(path: str) -> str:
    return UUID_RE.sub("{id}", path)


@dataclass
class RequestWindow:
    """Ventana de tiempo para contar las solicitudes que recibieron ciertos contenedores."""

    containers: tuple[str, ...]
    started: float = field(default_factory=time.time)
    ended: float | None = None

    def close(self) -> None:
        # Los registros llegan con un pequeño retraso.
        time.sleep(0.5)
        self.ended = time.time()

    def _inside(self, line: str) -> bool:
        stamp = line.split(" ", 1)[0]
        try:
            moment = datetime.strptime(stamp[:26].rstrip("Z"), "%Y-%m-%dT%H:%M:%S.%f").replace(tzinfo=UTC).timestamp()
        except ValueError:
            return False
        return self.started - 0.05 <= moment <= (self.ended or time.time())

    def counts(self) -> dict[str, int]:
        if self.ended is None:
            self.close()
        total: Counter[str] = Counter()
        for container in self.containers:
            # `docker logs --since/--until` redondea al segundo: se piden unos segundos de margen y se filtra
            # cada línea por su marca de tiempo (`-t`, RFC 3339 con nanosegundos, UTC).
            output = _docker(
                ["logs", "-t", "--since", _rfc3339(self.started - 2), "--until", _rfc3339(self.ended + 2), container]
            )
            short = container.removeprefix("sio-it-").removesuffix("-service")
            inside = "\n".join(line for line in output.splitlines() if self._inside(line))
            for match in ACCESS_LINE.finditer(inside):
                path = normalize_path(match.group("path"))
                if path.startswith("/health"):
                    continue
                total[f"{short} {match.group('method')} {path}"] += 1
        return dict(sorted(total.items()))


def read_source(container: str, variable: str) -> str:
    """Valor de UNA variable de entorno del contenedor (sin leer las demás, que llevan secretos)."""
    template = (
        "{{range .Config.Env}}{{if eq (index (split . \"=\") 0) \"" + variable + "\"}}"
        "{{index (split . \"=\") 1}}{{end}}{{end}}"
    )
    output = subprocess.run(
        ["docker", "inspect", "-f", template, container], capture_output=True, text=True, timeout=30, check=False
    )
    return output.stdout.strip() or "http"


# --------------------------------------------------------------------------- casos


class CaseMismatch(AssertionError):
    pass


class CaseBook:
    """Graba o compara los casos de un módulo de caracterización."""

    def __init__(self, module: str, *, record: bool = RECORD, directory: Path = CASES_DIR) -> None:
        self.module = module
        self.record = record
        self.path = directory / f"{module}.json"
        self._recorded: dict[str, Any] = {}
        if self.path.exists():
            self._recorded = json.loads(self.path.read_text(encoding="utf-8")).get("cases", {})
        self._current: dict[str, Any] = {}
        self.requests: dict[str, dict[str, int]] = {}

    def check(self, name: str, case: Mapping[str, Any], *, requests: Mapping[str, int] | None = None) -> None:
        """Graba el caso o lo compara (estado, cuerpo y efectos). Las solicitudes se guardan aparte."""
        observed = dict(case)
        self._current[name] = observed
        if requests is not None:
            self.requests[name] = dict(requests)
        if self.record:
            return
        if name not in self._recorded:
            raise CaseMismatch(f"{self.module}:{name} no está grabado; grábalo con SIO_CHARACTERIZATION_RECORD=1.")
        expected = self._recorded[name]["case"]
        if expected != observed:
            raise CaseMismatch(
                f"{self.module}:{name} cambió.\nGrabado:  {json.dumps(expected, ensure_ascii=False, sort_keys=True)}\n"
                f"Observado: {json.dumps(observed, ensure_ascii=False, sort_keys=True)}"
            )

    def recorded_requests(self, name: str) -> dict[str, int]:
        return dict(self._recorded.get(name, {}).get("requests", {}))

    def save(self, *, source: str) -> Path | None:
        """Escribe el archivo de casos (solo al grabar)."""
        if not self.record:
            return None
        CASES_DIR.mkdir(parents=True, exist_ok=True)
        payload = {
            "module": self.module,
            "recorded_with": source,
            "cases": {
                name: {"case": case, "requests": self.requests.get(name, {})}
                for name, case in sorted(self._current.items())
            },
        }
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return self.path


def matching(counts: Mapping[str, int], fragments: Iterable[str]) -> int:
    """Suma de solicitudes cuyo destino contiene alguno de los fragmentos."""
    fragments = tuple(fragments)
    return sum(value for key, value in counts.items() if any(fragment in key for fragment in fragments))
