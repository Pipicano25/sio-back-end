"""seed colombia identification type rules

Revision ID: 0003_seed_co_rules
Revises: 0002_ident_type_rules
Create Date: 2026-09-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0003_seed_co_rules"
down_revision: Union[str, Sequence[str], None] = "0002_ident_type_rules"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


COLOMBIA_COUNTRY_ID = "cf160c2d-b6de-4ef5-9257-a0a8539058d9"
SYSTEM_ACTOR_ID = "00000000-0000-0000-0000-000000000001"

RULE_IDS = [
    "bfc6d4df-64bb-563f-97e1-0dcd5a679d01",
    "28193d31-8d51-530e-8421-7a69167833d5",
    "18cc6a6b-8933-5791-b57f-3ac5d57b6502",
    "a3e411aa-1175-56b5-93fd-1bbbc22c1daf",
    "343c2e3d-2d56-5d72-849d-36fd7afccfa4",
]


def upgrade() -> None:
    """Upgrade schema."""
    connection = op.get_bind()

    rules = [
        {
            "id": RULE_IDS[0],
            "party_kind": "PERSON",
            "country_id": COLOMBIA_COUNTRY_ID,
            "identification_type": "NATIONAL_ID",
            "number_pattern": "^[0-9]{6,10}$",
            "number_pattern_description": (
                "La cedula colombiana debe contener solo numeros "
                "y tener entre 6 y 10 digitos."
            ),
            "example_value": "1234567890",
            "created_by": SYSTEM_ACTOR_ID,
            "updated_by": SYSTEM_ACTOR_ID,
        },
        {
            "id": RULE_IDS[1],
            "party_kind": "PERSON",
            "country_id": COLOMBIA_COUNTRY_ID,
            "identification_type": "FOREIGN_ID",
            "number_pattern": "^[A-Z0-9]{3,20}$",
            "number_pattern_description": (
                "La identificacion extranjera debe contener letras "
                "mayusculas o numeros entre 3 y 20 caracteres."
            ),
            "example_value": "E123456",
            "created_by": SYSTEM_ACTOR_ID,
            "updated_by": SYSTEM_ACTOR_ID,
        },
        {
            "id": RULE_IDS[2],
            "party_kind": "PERSON",
            "country_id": COLOMBIA_COUNTRY_ID,
            "identification_type": "PASSPORT",
            "number_pattern": "^[A-Z0-9]{6,20}$",
            "number_pattern_description": (
                "El pasaporte debe contener letras mayusculas o numeros "
                "entre 6 y 20 caracteres."
            ),
            "example_value": "AB123456",
            "created_by": SYSTEM_ACTOR_ID,
            "updated_by": SYSTEM_ACTOR_ID,
        },
        {
            "id": RULE_IDS[3],
            "party_kind": "PERSON",
            "country_id": COLOMBIA_COUNTRY_ID,
            "identification_type": "TAX_ID",
            "number_pattern": "^[0-9]{5,15}(-[0-9])?$",
            "number_pattern_description": (
                "El NIT colombiano debe contener numeros y puede incluir "
                "digito de verificacion separado por guion."
            ),
            "example_value": "900123456-7",
            "created_by": SYSTEM_ACTOR_ID,
            "updated_by": SYSTEM_ACTOR_ID,
        },
        {
            "id": RULE_IDS[4],
            "party_kind": "ORGANIZATION",
            "country_id": COLOMBIA_COUNTRY_ID,
            "identification_type": "TAX_ID",
            "number_pattern": "^[0-9]{5,15}(-[0-9])?$",
            "number_pattern_description": (
                "El NIT colombiano de organizacion debe contener numeros "
                "y puede incluir digito de verificacion separado por guion."
            ),
            "example_value": "900123456-7",
            "created_by": SYSTEM_ACTOR_ID,
            "updated_by": SYSTEM_ACTOR_ID,
        },
    ]

    statement = sa.text(
        """
        INSERT INTO identification_type_rules (
            id,
            party_kind,
            country_id,
            identification_type,
            number_pattern,
            number_pattern_description,
            example_value,
            is_active,
            created_by,
            updated_by
        )
        VALUES (
            CAST(:id AS uuid),
            :party_kind,
            CAST(:country_id AS uuid),
            :identification_type,
            :number_pattern,
            :number_pattern_description,
            :example_value,
            true,
            CAST(:created_by AS uuid),
            CAST(:updated_by AS uuid)
        )
        ON CONFLICT (
            party_kind,
            country_id,
            identification_type
        )
        WHERE is_active = true
        DO NOTHING
        """
    )

    connection.execute(
        statement,
        rules,
    )


def downgrade() -> None:
    """Downgrade schema."""
    quoted_rule_ids = ", ".join(
        f"'{rule_id}'"
        for rule_id in RULE_IDS
    )

    op.execute(
        sa.text(
            f"""
            DELETE FROM identification_type_rules
            WHERE id IN ({quoted_rule_ids})
            """
        )
    )
