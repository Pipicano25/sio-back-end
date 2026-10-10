"""Números de identificación ficticios conformes a la regla vigente de Party Identity (research R-05).

El número se genera de forma determinista a partir de la corrida, la etiqueta y el intento, con el
patrón (`number_pattern`) de la regla activa: cada proceso de la corrida puede volver a calcularlo sin
guardarlo en ningún informe. Nunca son identificaciones reales verificadas.
"""

from __future__ import annotations

import random
import re

from .run_context import RunContext

MAX_TRIES = 500


def conforming_number(pattern: str, context: RunContext, label: str, attempt: int = 1) -> str:
    regex = re.compile(pattern)
    generator = random.Random(f"{context.run_uuid}:{label}:{attempt}")
    for _ in range(MAX_TRIES):
        length = generator.randint(8, 10)
        base = str(generator.randint(1, 9)) + "".join(generator.choice("0123456789") for _ in range(length - 1))
        for candidate in (f"{base}-{generator.randint(0, 9)}", base):
            if regex.fullmatch(candidate):
                return candidate
    raise ValueError(f"No se pudo generar un número que cumpla el patrón {pattern!r}")
