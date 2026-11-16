"""Lectura directa, de solo lectura, de las vistas de contrato de otro servicio (constitución 3.0.0, D27)."""

from sio_contract_read.engine import chunked, connect_options, create_contract_engine, read, read_one
from sio_contract_read.errors import cause_of, contract_errors
from sio_contract_read.settings import CONTRACT, HTTP, ContractReadConfigError, ContractReadSettings

__all__ = [
    "CONTRACT",
    "HTTP",
    "ContractReadConfigError",
    "ContractReadSettings",
    "cause_of",
    "chunked",
    "connect_options",
    "contract_errors",
    "create_contract_engine",
    "read",
    "read_one",
]

__version__ = "0.1.0"
