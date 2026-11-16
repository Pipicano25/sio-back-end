"""Traducción de errores de lectura a la indisponibilidad que ya expone cada consumidor (spec 025, R3).

```python
with contract_errors(lambda cause: client_unavailable("company", cause)):
    row = read_one(engine, SQL, {"id": company_id})
```

Cualquier error de base de datos (conexión rechazada, tiempo agotado, pool agotado, ``statement_timeout``,
permiso denegado) llega al consumidor como **la misma excepción** que hoy produce su adaptador HTTP cuando el
propietario no responde. El mensaje nunca incluye la URL ni datos de la consulta.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator
from contextlib import contextmanager

from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger("sio_contract_read")


def cause_of(exc: BaseException) -> str:
    """Causa estable y sin secretos para registros."""
    original = getattr(exc, "orig", None)
    code = getattr(original, "sqlstate", None)
    if code == "57014":
        return "tiempo_agotado"
    if code == "42501":
        return "permiso_denegado"
    name = type(original or exc).__name__
    if "Timeout" in name:
        return "pool_agotado"
    return f"error_base:{name}"


@contextmanager
def contract_errors(on_unavailable: Callable[[str], BaseException], *, dependency: str = "") -> Iterator[None]:
    """Convierte ``SQLAlchemyError`` en la excepción de indisponibilidad del consumidor."""
    try:
        yield
    except SQLAlchemyError as exc:
        cause = cause_of(exc)
        logger.warning("Lectura de contrato no disponible dependencia=%s causa=%s", dependency, cause)
        raise on_unavailable(cause) from None
