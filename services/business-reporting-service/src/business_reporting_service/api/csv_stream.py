"""CSV bajo demanda en flujo (spec 023, FR-023-40 a FR-023-46; `contracts/csv.md`).

Garantías del mecanismo (documentadas en el README):

1. **Antes del primer byte** se obtiene la primera página y el total de filas: un error de permisos, validación,
   dependencia o un total mayor que el máximo responde RFC 9457 (`4xx`/`503`), nunca un CSV.
2. **Un CSV completo siempre termina** con la fila `TOTAL FILAS,<n>`, escrita solo cuando todas las páginas se
   leyeron sin error (y, antes, las filas de totales del reporte). Es la prueba de completitud que no depende del
   cliente HTTP.
3. **Si un error ocurre a mitad de la transmisión**: no se escriben totales ni `TOTAL FILAS`; se escribe una última
   línea `#ERROR: reporte incompleto, trace_id=<id>` (una sola columna, que no puede confundirse con una fila del
   reporte) y se relanza la excepción. Uvicorn cierra entonces la conexión sin el bloque final de la codificación
   `chunked`; `curl` lo informa como transferencia incompleta y los navegadores habituales marcan la descarga como
   fallida, **pero eso depende del cliente**: lo que garantiza el servicio son los puntos 2 y 3.

Memoria acotada: una página del propietario y un búfer de texto que se vacía por fila. Sin archivos temporales.
Protección contra fórmulas (OWASP CSV Injection): toda celda de **texto** que empieza por `=`, `+`, `-`, `@`,
tabulación o retorno de carro se prefija con `'`; las columnas numéricas se escriben como números.
"""

from __future__ import annotations

import csv
import io
import logging
from collections.abc import AsyncIterator, Callable, Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from business_reporting_service.observability import SERVICE_LOGGER, current_trace_id

logger = logging.getLogger(SERVICE_LOGGER)
BOM = "﻿"
FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")
COMPLETE_MARKER = "TOTAL FILAS"
ERROR_MARKER = "#ERROR: reporte incompleto"


class Number:
    """Celda numérica: nunca se prefija (un importe negativo sigue siendo un número)."""

    __slots__ = ("value",)

    def __init__(self, value: Decimal | int | str | None) -> None:
        self.value = value


def cell(value: Any) -> str:
    """Valor de una celda, con la protección de fórmulas para el texto."""
    if value is None:
        return ""
    if isinstance(value, Number):
        return "" if value.value is None else (format(value.value, "f") if isinstance(value.value, Decimal) else str(value.value))
    if isinstance(value, bool):
        return "true" if value else "false"
    text = str(value)
    return "'" + text if text.startswith(FORMULA_PREFIXES) else text


def _line(writer_buffer: io.StringIO, writer, row: Sequence[Any]) -> str:
    writer.writerow([cell(value) for value in row])
    text = writer_buffer.getvalue()
    writer_buffer.seek(0)
    writer_buffer.truncate(0)
    return text


@dataclass
class CsvPlan:
    header: Sequence[str]
    first_rows: list[Sequence[Any]]
    """Filas de la primera página (ya leída antes de responder)."""
    next_pages: Callable[[], AsyncIterator[list[Sequence[Any]]]] | None
    """Páginas siguientes, leídas durante la transmisión."""
    totals: Callable[[], Iterable[Sequence[Any]]]
    """Filas de totales del reporte (se escriben solo al final y sin errores)."""


async def stream(plan: CsvPlan, *, bom: bool = True) -> AsyncIterator[str]:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\r\n")
    written = 0
    yield (BOM if bom else "") + _line(buffer, writer, plan.header)
    for row in plan.first_rows:
        written += 1
        yield _line(buffer, writer, row)
    try:
        if plan.next_pages is not None:
            async for page in plan.next_pages():
                chunk = []
                for row in page:
                    written += 1
                    chunk.append(_line(buffer, writer, row))
                yield "".join(chunk)
        tail = [_line(buffer, writer, row) for row in plan.totals()]
        tail.append(_line(buffer, writer, [COMPLETE_MARKER, Number(written)]))
        yield "".join(tail)
    except Exception:
        logger.exception("CSV interrumpido después de iniciar la transmisión filas_escritas=%d", written)
        yield f"{ERROR_MARKER}, trace_id={current_trace_id() or '-'}\r\n"
        raise
