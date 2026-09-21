"""relax identification codes

Revision ID: 0007_relax_id_codes
Revises: 0006_reset_co_id_types
Create Date: 2026-09-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "0007_relax_id_codes"
down_revision: Union[str, Sequence[str], None] = "0006_reset_co_id_types"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint(
        "ck_person_identities_identification_type",
        "person_identities",
        type_="check",
    )
    op.drop_constraint(
        "ck_identification_type_rules_identification_type",
        "identification_type_rules",
        type_="check",
    )
    op.drop_constraint(
        "ck_identification_type_rules_sigla",
        "identification_type_rules",
        type_="check",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.create_check_constraint(
        "ck_person_identities_identification_type",
        "person_identities",
        "identification_type IN ('RC', 'TI', 'CC', 'CE', 'NIT')",
    )
    op.create_check_constraint(
        "ck_identification_type_rules_identification_type",
        "identification_type_rules",
        (
            "identification_type IN ("
            "'CIVIL_REGISTRY', "
            "'IDENTITY_CARD_MODERN', "
            "'CITIZEN_ID_MODERN', "
            "'CITIZEN_ID_OLD', "
            "'FOREIGN_CARD', "
            "'TAX_ID', "
            "'IDENTITY_CARD_OLD'"
            ")"
        ),
    )
    op.create_check_constraint(
        "ck_identification_type_rules_sigla",
        "identification_type_rules",
        "sigla IN ('RC', 'TI', 'CC', 'CE', 'NIT')",
    )
