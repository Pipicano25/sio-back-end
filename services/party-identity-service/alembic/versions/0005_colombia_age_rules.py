"""add colombia age rules

Revision ID: 0005_co_age_rules
Revises: 0004_expand_co_rules
Create Date: 2026-09-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0005_co_age_rules"
down_revision: Union[str, Sequence[str], None] = "0004_expand_co_rules"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


COLOMBIA_COUNTRY_ID = "cf160c2d-b6de-4ef5-9257-a0a8539058d9"
SYSTEM_ACTOR_ID = "00000000-0000-0000-0000-000000000001"


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "identification_type_rules",
        sa.Column(
            "min_age_years",
            sa.Integer(),
            nullable=True,
        ),
    )
    op.add_column(
        "identification_type_rules",
        sa.Column(
            "max_age_years",
            sa.Integer(),
            nullable=True,
        ),
    )
    op.create_check_constraint(
        "ck_identification_type_rules_min_age_non_negative",
        "identification_type_rules",
        "min_age_years IS NULL OR min_age_years >= 0",
    )
    op.create_check_constraint(
        "ck_identification_type_rules_max_age_non_negative",
        "identification_type_rules",
        "max_age_years IS NULL OR max_age_years >= 0",
    )
    op.create_check_constraint(
        "ck_identification_type_rules_age_range",
        "identification_type_rules",
        (
            "min_age_years IS NULL OR max_age_years IS NULL "
            "OR max_age_years >= min_age_years"
        ),
    )

    connection = op.get_bind()

    connection.execute(
        sa.text(
            """
            UPDATE identification_type_rules
            SET
                is_active = false,
                updated_by = CAST(:actor_id AS uuid),
                updated_at = now()
            WHERE country_id = CAST(:country_id AS uuid)
              AND party_kind = 'PERSON'
              AND is_active = true
              AND identification_type NOT IN (
                  'CIVIL_REGISTRY',
                  'IDENTITY_CARD',
                  'CITIZEN_ID',
                  'FOREIGN_CARD',
                  'TAX_ID'
              )
            """
        ),
        {
            "actor_id": SYSTEM_ACTOR_ID,
            "country_id": COLOMBIA_COUNTRY_ID,
        },
    )

    connection.execute(
        sa.text(
            """
            UPDATE identification_type_rules
            SET
                is_active = false,
                updated_by = CAST(:actor_id AS uuid),
                updated_at = now()
            WHERE country_id = CAST(:country_id AS uuid)
              AND party_kind = 'ORGANIZATION'
              AND is_active = true
              AND identification_type <> 'TAX_ID'
            """
        ),
        {
            "actor_id": SYSTEM_ACTOR_ID,
            "country_id": COLOMBIA_COUNTRY_ID,
        },
    )

    rules = [
        {
            "id": "9d596676-d4c4-5141-b378-2c9eb3c9e4ae",
            "party_kind": "PERSON",
            "identification_type": "CIVIL_REGISTRY",
            "number_pattern": "^[0-9]{10}$",
            "number_pattern_description": (
                "El registro civil colombiano corresponde al NUIP, "
                "debe contener 10 digitos numericos y aplica de 0 a 6 anos."
            ),
            "example_value": "1234567890",
            "min_age_years": 0,
            "max_age_years": 6,
        },
        {
            "id": "b901502a-4162-58aa-b199-1563bae98636",
            "party_kind": "PERSON",
            "identification_type": "IDENTITY_CARD",
            "number_pattern": "^([0-9]{10}|[0-9]{11})$",
            "number_pattern_description": (
                "La tarjeta de identidad colombiana debe contener 10 "
                "digitos en formato moderno NUIP u 11 digitos en formato "
                "historico NIP, y aplica de 7 a 17 anos."
            ),
            "example_value": "1234567890",
            "min_age_years": 7,
            "max_age_years": 17,
        },
        {
            "id": "7c7fd89f-ab95-5c96-afe7-8f5b6b3c9555",
            "party_kind": "PERSON",
            "identification_type": "CITIZEN_ID",
            "number_pattern": "^([0-9]{3,8}|[0-9]{10})$",
            "number_pattern_description": (
                "La cedula de ciudadania colombiana debe contener 10 "
                "digitos en formato moderno NUIP o entre 3 y 8 digitos "
                "en formato historico, y aplica desde los 18 anos."
            ),
            "example_value": "1234567890",
            "min_age_years": 18,
            "max_age_years": None,
        },
        {
            "id": "3492d46b-f4bd-5578-a1d2-7442ecf2b0e8",
            "party_kind": "PERSON",
            "identification_type": "FOREIGN_CARD",
            "number_pattern": "^[0-9]{3,7}$",
            "number_pattern_description": (
                "La cedula de extranjeria debe contener entre 3 y 7 "
                "digitos numericos y aplica desde los 7 anos."
            ),
            "example_value": "1234567",
            "min_age_years": 7,
            "max_age_years": None,
        },
        {
            "id": "a3e411aa-1175-56b5-93fd-1bbbc22c1daf",
            "party_kind": "PERSON",
            "identification_type": "TAX_ID",
            "number_pattern": "^[A-Z0-9]{4,11}-[0-9]$",
            "number_pattern_description": (
                "El NIT debe contener una base alfanumerica de 4 a 11 "
                "caracteres, guion y digito de verificacion."
            ),
            "example_value": "900123456-7",
            "min_age_years": None,
            "max_age_years": None,
        },
        {
            "id": "343c2e3d-2d56-5d72-849d-36fd7afccfa4",
            "party_kind": "ORGANIZATION",
            "identification_type": "TAX_ID",
            "number_pattern": "^[A-Z0-9]{4,11}-[0-9]$",
            "number_pattern_description": (
                "El NIT de organizacion debe contener una base "
                "alfanumerica de 4 a 11 caracteres, guion y digito "
                "de verificacion."
            ),
            "example_value": "900123456-7",
            "min_age_years": None,
            "max_age_years": None,
        },
    ]

    connection.execute(
        sa.text(
            """
            INSERT INTO identification_type_rules (
                id,
                party_kind,
                country_id,
                identification_type,
                number_pattern,
                number_pattern_description,
                example_value,
                min_age_years,
                max_age_years,
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
                :min_age_years,
                :max_age_years,
                true,
                CAST(:actor_id AS uuid),
                CAST(:actor_id AS uuid)
            )
            ON CONFLICT (
                party_kind,
                country_id,
                identification_type
            )
            WHERE is_active = true
            DO UPDATE SET
                number_pattern = EXCLUDED.number_pattern,
                number_pattern_description =
                    EXCLUDED.number_pattern_description,
                example_value = EXCLUDED.example_value,
                min_age_years = EXCLUDED.min_age_years,
                max_age_years = EXCLUDED.max_age_years,
                updated_by = EXCLUDED.updated_by,
                updated_at = now()
            """
        ),
        [
            {
                **rule,
                "country_id": COLOMBIA_COUNTRY_ID,
                "actor_id": SYSTEM_ACTOR_ID,
            }
            for rule in rules
        ],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "ck_identification_type_rules_age_range",
        "identification_type_rules",
        type_="check",
    )
    op.drop_constraint(
        "ck_identification_type_rules_max_age_non_negative",
        "identification_type_rules",
        type_="check",
    )
    op.drop_constraint(
        "ck_identification_type_rules_min_age_non_negative",
        "identification_type_rules",
        type_="check",
    )
    op.drop_column(
        "identification_type_rules",
        "max_age_years",
    )
    op.drop_column(
        "identification_type_rules",
        "min_age_years",
    )
