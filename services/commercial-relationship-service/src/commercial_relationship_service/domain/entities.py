"""Vocabulario de las entidades del dominio (data-model.md).

Las entidades persistentes se representan con los modelos SQLAlchemy de
`infrastructure/models.py`; aquí viven los valores cerrados que comparten las
capas.
"""

from commercial_relationship_service.domain.rules import ORGANIZATION, PERSON
from commercial_relationship_service.domain.status import ACTIVE, BLOCKED, INACTIVE

CUSTOMER_KINDS = (PERSON, ORGANIZATION)
PRODUCT_STATUSES = (ACTIVE, INACTIVE)
CUSTOMER_STATUSES = (ACTIVE, INACTIVE)
SUPPLIER_STATUSES = (ACTIVE, INACTIVE, BLOCKED)

INTERNAL_CODE_MAX = 60
REFERENCE_CODE_MAX = 100
DISPLAY_NAME_MAX = 200
SHORT_NAME_MAX = 160
BLOCK_REASON_MAX = 500
