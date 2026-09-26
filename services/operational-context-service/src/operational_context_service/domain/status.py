"""Estados de uso de empresas y sucursales (D7)."""

from typing import Literal

EntityStatus = Literal["ACTIVE", "INACTIVE"]

ACTIVE: EntityStatus = "ACTIVE"
INACTIVE: EntityStatus = "INACTIVE"
