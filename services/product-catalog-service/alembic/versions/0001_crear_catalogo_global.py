"""Crear el catálogo global de productos (16 tablas y extensión pg_trgm).

Revision ID: 0001
Revises: 
Create Date: 2026-09-25 02:30:27.281648

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Crea la extensión pg_trgm y las 16 tablas del catálogo global."""
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.create_table('global_brands',
    sa.Column('code', sa.String(length=50), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_by', sa.String(length=255), nullable=False),
    sa.Column('updated_by', sa.String(length=255), nullable=False),
    sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.Column('status', sa.String(length=20), server_default=sa.text("'ACTIVE'"), nullable=False),
    sa.CheckConstraint("code = upper(btrim(code)) AND code <> ''", name=op.f('ck_global_brands_code_normalized')),
    sa.CheckConstraint("status IN ('ACTIVE','INACTIVE')", name=op.f('ck_global_brands_status')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_global_brands')),
    sa.UniqueConstraint('code', name='uq_global_brands_code')
    )
    op.create_table('global_categories',
    sa.Column('parent_category_id', sa.Uuid(), nullable=True),
    sa.Column('code', sa.String(length=50), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_by', sa.String(length=255), nullable=False),
    sa.Column('updated_by', sa.String(length=255), nullable=False),
    sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.Column('status', sa.String(length=20), server_default=sa.text("'ACTIVE'"), nullable=False),
    sa.CheckConstraint("code = upper(btrim(code)) AND code <> ''", name=op.f('ck_global_categories_code_normalized')),
    sa.CheckConstraint("status IN ('ACTIVE','INACTIVE')", name=op.f('ck_global_categories_status')),
    sa.CheckConstraint('parent_category_id IS NULL OR parent_category_id <> id', name=op.f('ck_global_categories_not_self_parent')),
    sa.ForeignKeyConstraint(['parent_category_id'], ['global_categories.id'], name=op.f('fk_global_categories_parent_category_id_global_categories'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_global_categories')),
    sa.UniqueConstraint('code', name='uq_global_categories_code')
    )
    op.create_index('ix_global_categories_parent_category_id', 'global_categories', ['parent_category_id'], unique=False)
    op.create_table('global_packaging_types',
    sa.Column('code', sa.String(length=50), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_by', sa.String(length=255), nullable=False),
    sa.Column('updated_by', sa.String(length=255), nullable=False),
    sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.Column('status', sa.String(length=20), server_default=sa.text("'ACTIVE'"), nullable=False),
    sa.CheckConstraint("code = upper(btrim(code)) AND code <> ''", name=op.f('ck_global_packaging_types_code_normalized')),
    sa.CheckConstraint("status IN ('ACTIVE','INACTIVE')", name=op.f('ck_global_packaging_types_status')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_global_packaging_types')),
    sa.UniqueConstraint('code', name='uq_global_packaging_types_code')
    )
    op.create_table('global_product_group_types',
    sa.Column('code', sa.String(length=50), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('allows_multiple', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('display_order', sa.SmallInteger(), server_default=sa.text('0'), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_by', sa.String(length=255), nullable=False),
    sa.Column('updated_by', sa.String(length=255), nullable=False),
    sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.Column('status', sa.String(length=20), server_default=sa.text("'ACTIVE'"), nullable=False),
    sa.CheckConstraint("code = upper(btrim(code)) AND code <> ''", name=op.f('ck_global_product_group_types_code_normalized')),
    sa.CheckConstraint("status IN ('ACTIVE','INACTIVE')", name=op.f('ck_global_product_group_types_status')),
    sa.CheckConstraint('display_order >= 0', name=op.f('ck_global_product_group_types_display_order')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_global_product_group_types')),
    sa.UniqueConstraint('code', name='uq_global_product_group_types_code')
    )
    op.create_table('global_units_of_measure',
    sa.Column('code', sa.String(length=20), nullable=False),
    sa.Column('name', sa.String(length=80), nullable=False),
    sa.Column('symbol', sa.String(length=16), nullable=False),
    sa.Column('measurement_type', sa.String(length=30), nullable=False),
    sa.Column('allows_decimals', sa.Boolean(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_by', sa.String(length=255), nullable=False),
    sa.Column('updated_by', sa.String(length=255), nullable=False),
    sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.Column('status', sa.String(length=20), server_default=sa.text("'ACTIVE'"), nullable=False),
    sa.CheckConstraint("code = upper(btrim(code)) AND code <> ''", name=op.f('ck_global_units_of_measure_code_normalized')),
    sa.CheckConstraint("measurement_type IN ('UNIT','MASS','VOLUME','LENGTH','AREA')", name=op.f('ck_global_units_of_measure_measurement_type')),
    sa.CheckConstraint("status IN ('ACTIVE','INACTIVE')", name=op.f('ck_global_units_of_measure_status')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_global_units_of_measure')),
    sa.UniqueConstraint('code', name='uq_global_units_of_measure_code')
    )
    op.create_table('global_product_groups',
    sa.Column('group_type_id', sa.Uuid(), nullable=False),
    sa.Column('parent_group_id', sa.Uuid(), nullable=True),
    sa.Column('code', sa.String(length=50), nullable=False),
    sa.Column('name', sa.String(length=160), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_by', sa.String(length=255), nullable=False),
    sa.Column('updated_by', sa.String(length=255), nullable=False),
    sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.Column('status', sa.String(length=20), server_default=sa.text("'ACTIVE'"), nullable=False),
    sa.CheckConstraint("code = upper(btrim(code)) AND code <> ''", name=op.f('ck_global_product_groups_code_normalized')),
    sa.CheckConstraint("status IN ('ACTIVE','INACTIVE')", name=op.f('ck_global_product_groups_status')),
    sa.CheckConstraint('parent_group_id IS NULL OR parent_group_id <> id', name=op.f('ck_global_product_groups_not_self_parent')),
    sa.ForeignKeyConstraint(['group_type_id'], ['global_product_group_types.id'], name=op.f('fk_global_product_groups_group_type_id_global_product_group_types'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['parent_group_id', 'group_type_id'], ['global_product_groups.id', 'global_product_groups.group_type_id'], name='fk_global_product_groups_parent_same_type', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_global_product_groups')),
    sa.UniqueConstraint('group_type_id', 'code', name='uq_global_product_groups_type_code'),
    sa.UniqueConstraint('id', 'group_type_id', name='uq_global_product_groups_id_type')
    )
    op.create_index('ix_global_product_groups_parent_group_id', 'global_product_groups', ['parent_group_id'], unique=False)
    op.create_table('global_products',
    sa.Column('product_type', sa.String(length=20), nullable=False),
    sa.Column('canonical_name', sa.String(length=200), nullable=False),
    sa.Column('canonical_name_key', sa.String(length=200), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('global_brand_id', sa.Uuid(), nullable=True),
    sa.Column('manufacturer_organization_id', sa.Uuid(), nullable=True),
    sa.Column('base_unit_id', sa.Uuid(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_by', sa.String(length=255), nullable=False),
    sa.Column('updated_by', sa.String(length=255), nullable=False),
    sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.Column('status', sa.String(length=20), server_default=sa.text("'ACTIVE'"), nullable=False),
    sa.Column('first_used_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('first_used_by', sa.String(length=255), nullable=True),
    sa.Column('first_use_source', sa.String(length=20), nullable=True),
    sa.CheckConstraint("first_use_source IS NULL OR first_use_source IN ('ADOPTION','MANUAL')", name=op.f('ck_global_products_first_use_source')),
    sa.CheckConstraint("product_type IN ('GOOD')", name=op.f('ck_global_products_product_type')),
    sa.CheckConstraint("status IN ('ACTIVE','INACTIVE')", name=op.f('ck_global_products_status')),
    sa.CheckConstraint('(first_used_at IS NULL AND first_used_by IS NULL AND first_use_source IS NULL) OR (first_used_at IS NOT NULL AND first_used_by IS NOT NULL AND first_use_source IS NOT NULL)', name=op.f('ck_global_products_first_use_consistent')),
    sa.ForeignKeyConstraint(['base_unit_id'], ['global_units_of_measure.id'], name=op.f('fk_global_products_base_unit_id_global_units_of_measure'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['global_brand_id'], ['global_brands.id'], name=op.f('fk_global_products_global_brand_id_global_brands'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_global_products'))
    )
    op.create_index('ix_global_products_base_unit_id', 'global_products', ['base_unit_id'], unique=False)
    op.create_index('ix_global_products_canonical_name_key_trgm', 'global_products', ['canonical_name_key'], unique=False, postgresql_using='gin', postgresql_ops={'canonical_name_key': 'gin_trgm_ops'})
    op.create_index('ix_global_products_duplicate_key', 'global_products', ['canonical_name_key', 'global_brand_id'], unique=False)
    op.create_index('ix_global_products_global_brand_id', 'global_products', ['global_brand_id'], unique=False)
    op.create_index('ix_global_products_manufacturer_organization_id', 'global_products', ['manufacturer_organization_id'], unique=False)
    op.create_index('ix_global_products_status', 'global_products', ['status'], unique=False)
    op.create_table('product_attribute_definitions',
    sa.Column('code', sa.String(length=80), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('data_type', sa.String(length=20), nullable=False),
    sa.Column('unit_of_measure_id', sa.Uuid(), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_by', sa.String(length=255), nullable=False),
    sa.Column('updated_by', sa.String(length=255), nullable=False),
    sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.Column('status', sa.String(length=20), server_default=sa.text("'ACTIVE'"), nullable=False),
    sa.CheckConstraint("btrim(description) <> ''", name=op.f('ck_product_attribute_definitions_description_not_blank')),
    sa.CheckConstraint("code = upper(btrim(code)) AND code <> ''", name=op.f('ck_product_attribute_definitions_code_normalized')),
    sa.CheckConstraint("data_type IN ('TEXT','INTEGER','DECIMAL','BOOLEAN','DATE','OPTION')", name=op.f('ck_product_attribute_definitions_data_type')),
    sa.CheckConstraint("status IN ('ACTIVE','INACTIVE')", name=op.f('ck_product_attribute_definitions_status')),
    sa.CheckConstraint("unit_of_measure_id IS NULL OR data_type IN ('INTEGER','DECIMAL')", name=op.f('ck_product_attribute_definitions_unit_numeric')),
    sa.ForeignKeyConstraint(['unit_of_measure_id'], ['global_units_of_measure.id'], name=op.f('fk_product_attribute_definitions_unit_of_measure_id_global_units_of_measure'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_product_attribute_definitions')),
    sa.UniqueConstraint('code', name='uq_product_attribute_definitions_code')
    )
    op.create_table('global_category_attributes',
    sa.Column('global_category_id', sa.Uuid(), nullable=False),
    sa.Column('attribute_definition_id', sa.Uuid(), nullable=False),
    sa.Column('is_required', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('is_filterable', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('display_order', sa.SmallInteger(), server_default=sa.text('0'), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_by', sa.String(length=255), nullable=False),
    sa.Column('updated_by', sa.String(length=255), nullable=False),
    sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.Column('status', sa.String(length=20), server_default=sa.text("'ACTIVE'"), nullable=False),
    sa.CheckConstraint("status IN ('ACTIVE','INACTIVE')", name=op.f('ck_global_category_attributes_status')),
    sa.CheckConstraint('display_order >= 0', name=op.f('ck_global_category_attributes_display_order')),
    sa.ForeignKeyConstraint(['attribute_definition_id'], ['product_attribute_definitions.id'], name=op.f('fk_global_category_attributes_attribute_definition_id_product_attribute_definitions'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['global_category_id'], ['global_categories.id'], name=op.f('fk_global_category_attributes_global_category_id_global_categories'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_global_category_attributes')),
    sa.UniqueConstraint('global_category_id', 'attribute_definition_id', name='uq_global_category_attributes_category_definition')
    )
    op.create_index('ix_global_category_attributes_attribute_definition_id', 'global_category_attributes', ['attribute_definition_id'], unique=False)
    op.create_table('global_product_categories',
    sa.Column('global_product_id', sa.Uuid(), nullable=False),
    sa.Column('global_category_id', sa.Uuid(), nullable=False),
    sa.Column('is_primary', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_by', sa.String(length=255), nullable=False),
    sa.Column('updated_by', sa.String(length=255), nullable=False),
    sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.Column('status', sa.String(length=20), server_default=sa.text("'ACTIVE'"), nullable=False),
    sa.CheckConstraint("NOT is_primary OR status = 'ACTIVE'", name=op.f('ck_global_product_categories_primary_active')),
    sa.CheckConstraint("status IN ('ACTIVE','INACTIVE')", name=op.f('ck_global_product_categories_status')),
    sa.ForeignKeyConstraint(['global_category_id'], ['global_categories.id'], name=op.f('fk_global_product_categories_global_category_id_global_categories'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['global_product_id'], ['global_products.id'], name=op.f('fk_global_product_categories_global_product_id_global_products'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_global_product_categories')),
    sa.UniqueConstraint('global_product_id', 'global_category_id', name='uq_global_product_categories_product_category')
    )
    op.create_index('ix_global_product_categories_global_category_id', 'global_product_categories', ['global_category_id'], unique=False)
    op.create_index('uq_global_product_categories_primary', 'global_product_categories', ['global_product_id'], unique=True, postgresql_where=sa.text("is_primary AND status = 'ACTIVE'"))
    op.create_table('global_product_group_assignments',
    sa.Column('global_product_id', sa.Uuid(), nullable=False),
    sa.Column('global_product_group_id', sa.Uuid(), nullable=False),
    sa.Column('group_type_id', sa.Uuid(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_by', sa.String(length=255), nullable=False),
    sa.Column('updated_by', sa.String(length=255), nullable=False),
    sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.Column('status', sa.String(length=20), server_default=sa.text("'ACTIVE'"), nullable=False),
    sa.CheckConstraint("status IN ('ACTIVE','INACTIVE')", name=op.f('ck_global_product_group_assignments_status')),
    sa.ForeignKeyConstraint(['global_product_group_id', 'group_type_id'], ['global_product_groups.id', 'global_product_groups.group_type_id'], name='fk_global_product_group_assignments_group_type', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['global_product_id'], ['global_products.id'], name=op.f('fk_global_product_group_assignments_global_product_id_global_products'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_global_product_group_assignments')),
    sa.UniqueConstraint('global_product_id', 'global_product_group_id', name='uq_global_product_group_assignments_product_group')
    )
    op.create_index('ix_global_product_group_assignments_group_id', 'global_product_group_assignments', ['global_product_group_id'], unique=False)
    op.create_index('ix_global_product_group_assignments_product_type', 'global_product_group_assignments', ['global_product_id', 'group_type_id'], unique=False, postgresql_where=sa.text("status = 'ACTIVE'"))
    op.create_table('global_product_presentations',
    sa.Column('global_product_id', sa.Uuid(), nullable=False),
    sa.Column('code', sa.String(length=60), nullable=False),
    sa.Column('name', sa.String(length=160), nullable=False),
    sa.Column('packaging_type_id', sa.Uuid(), nullable=True),
    sa.Column('base_quantity', sa.Numeric(precision=18, scale=8), server_default=sa.text('1'), nullable=False),
    sa.Column('content_quantity', sa.Numeric(precision=18, scale=4), nullable=True),
    sa.Column('content_unit_id', sa.Uuid(), nullable=True),
    sa.Column('display_order', sa.SmallInteger(), server_default=sa.text('0'), nullable=False),
    sa.Column('is_base', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_by', sa.String(length=255), nullable=False),
    sa.Column('updated_by', sa.String(length=255), nullable=False),
    sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.Column('status', sa.String(length=20), server_default=sa.text("'ACTIVE'"), nullable=False),
    sa.Column('first_used_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('first_used_by', sa.String(length=255), nullable=True),
    sa.Column('first_use_source', sa.String(length=20), nullable=True),
    sa.CheckConstraint("NOT is_base OR status = 'ACTIVE'", name=op.f('ck_global_product_presentations_base_active')),
    sa.CheckConstraint("code = upper(btrim(code)) AND code <> ''", name=op.f('ck_global_product_presentations_code_normalized')),
    sa.CheckConstraint("first_use_source IS NULL OR first_use_source IN ('ADOPTION','MANUAL')", name=op.f('ck_global_product_presentations_first_use_source')),
    sa.CheckConstraint("status IN ('ACTIVE','INACTIVE')", name=op.f('ck_global_product_presentations_status')),
    sa.CheckConstraint('(content_quantity IS NULL) = (content_unit_id IS NULL)', name=op.f('ck_global_product_presentations_content_pair')),
    sa.CheckConstraint('(first_used_at IS NULL AND first_used_by IS NULL AND first_use_source IS NULL) OR (first_used_at IS NOT NULL AND first_used_by IS NOT NULL AND first_use_source IS NOT NULL)', name=op.f('ck_global_product_presentations_first_use_consistent')),
    sa.CheckConstraint('NOT is_base OR base_quantity = 1', name=op.f('ck_global_product_presentations_base_factor')),
    sa.CheckConstraint('base_quantity > 0', name=op.f('ck_global_product_presentations_base_quantity_positive')),
    sa.CheckConstraint('content_quantity IS NULL OR content_quantity > 0', name=op.f('ck_global_product_presentations_content_positive')),
    sa.CheckConstraint('display_order >= 0', name=op.f('ck_global_product_presentations_display_order')),
    sa.ForeignKeyConstraint(['content_unit_id'], ['global_units_of_measure.id'], name=op.f('fk_global_product_presentations_content_unit_id_global_units_of_measure'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['global_product_id'], ['global_products.id'], name=op.f('fk_global_product_presentations_global_product_id_global_products'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['packaging_type_id'], ['global_packaging_types.id'], name=op.f('fk_global_product_presentations_packaging_type_id_global_packaging_types'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_global_product_presentations')),
    sa.UniqueConstraint('global_product_id', 'code', name='uq_global_product_presentations_product_code'),
    sa.UniqueConstraint('id', 'global_product_id', name='uq_global_product_presentations_id_product')
    )
    op.create_index('uq_global_product_presentations_base', 'global_product_presentations', ['global_product_id'], unique=True, postgresql_where=sa.text("is_base AND status = 'ACTIVE'"))
    op.create_table('product_assets',
    sa.Column('global_product_id', sa.Uuid(), nullable=False),
    sa.Column('asset_type', sa.String(length=30), nullable=False),
    sa.Column('file_name', sa.String(length=255), nullable=False),
    sa.Column('storage_uri', sa.Text(), nullable=False),
    sa.Column('mime_type', sa.String(length=120), nullable=True),
    sa.Column('is_primary', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_by', sa.String(length=255), nullable=False),
    sa.Column('updated_by', sa.String(length=255), nullable=False),
    sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.Column('status', sa.String(length=20), server_default=sa.text("'ACTIVE'"), nullable=False),
    sa.CheckConstraint("NOT is_primary OR status = 'ACTIVE'", name=op.f('ck_product_assets_primary_active')),
    sa.CheckConstraint("asset_type IN ('IMAGE','TECHNICAL_SHEET','MANUAL','CERTIFICATE','OTHER')", name=op.f('ck_product_assets_asset_type')),
    sa.CheckConstraint("status IN ('ACTIVE','INACTIVE')", name=op.f('ck_product_assets_status')),
    sa.ForeignKeyConstraint(['global_product_id'], ['global_products.id'], name=op.f('fk_product_assets_global_product_id_global_products'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_product_assets'))
    )
    op.create_index('ix_product_assets_global_product_id', 'product_assets', ['global_product_id'], unique=False)
    op.create_index('uq_product_assets_primary', 'product_assets', ['global_product_id', 'asset_type'], unique=True, postgresql_where=sa.text("is_primary AND status = 'ACTIVE'"))
    op.create_table('product_attribute_options',
    sa.Column('attribute_definition_id', sa.Uuid(), nullable=False),
    sa.Column('code', sa.String(length=80), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('display_order', sa.SmallInteger(), server_default=sa.text('0'), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_by', sa.String(length=255), nullable=False),
    sa.Column('updated_by', sa.String(length=255), nullable=False),
    sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.Column('status', sa.String(length=20), server_default=sa.text("'ACTIVE'"), nullable=False),
    sa.CheckConstraint("code = upper(btrim(code)) AND code <> ''", name=op.f('ck_product_attribute_options_code_normalized')),
    sa.CheckConstraint("status IN ('ACTIVE','INACTIVE')", name=op.f('ck_product_attribute_options_status')),
    sa.CheckConstraint('display_order >= 0', name=op.f('ck_product_attribute_options_display_order')),
    sa.ForeignKeyConstraint(['attribute_definition_id'], ['product_attribute_definitions.id'], name=op.f('fk_product_attribute_options_attribute_definition_id_product_attribute_definitions'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_product_attribute_options')),
    sa.UniqueConstraint('attribute_definition_id', 'code', name='uq_product_attribute_options_definition_code'),
    sa.UniqueConstraint('id', 'attribute_definition_id', name='uq_product_attribute_options_id_definition')
    )
    op.create_table('global_product_attribute_values',
    sa.Column('global_product_id', sa.Uuid(), nullable=False),
    sa.Column('attribute_definition_id', sa.Uuid(), nullable=False),
    sa.Column('option_id', sa.Uuid(), nullable=True),
    sa.Column('text_value', sa.Text(), nullable=True),
    sa.Column('integer_value', sa.BigInteger(), nullable=True),
    sa.Column('decimal_value', sa.Numeric(precision=18, scale=8), nullable=True),
    sa.Column('boolean_value', sa.Boolean(), nullable=True),
    sa.Column('date_value', sa.Date(), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_by', sa.String(length=255), nullable=False),
    sa.Column('updated_by', sa.String(length=255), nullable=False),
    sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.CheckConstraint("text_value IS NULL OR btrim(text_value) <> ''", name=op.f('ck_global_product_attribute_values_text_not_blank')),
    sa.CheckConstraint('num_nonnulls(option_id, text_value, integer_value, decimal_value, boolean_value, date_value) = 1', name=op.f('ck_global_product_attribute_values_exactly_one')),
    sa.ForeignKeyConstraint(['attribute_definition_id'], ['product_attribute_definitions.id'], name=op.f('fk_global_product_attribute_values_attribute_definition_id_product_attribute_definitions'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['global_product_id'], ['global_products.id'], name=op.f('fk_global_product_attribute_values_global_product_id_global_products'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['option_id', 'attribute_definition_id'], ['product_attribute_options.id', 'product_attribute_options.attribute_definition_id'], name='fk_global_product_attribute_values_option_definition', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_global_product_attribute_values')),
    sa.UniqueConstraint('global_product_id', 'attribute_definition_id', name='uq_global_product_attribute_values_product_definition')
    )
    op.create_index('ix_global_product_attribute_values_attribute_definition_id', 'global_product_attribute_values', ['attribute_definition_id'], unique=False)
    op.create_table('global_product_identifiers',
    sa.Column('global_product_id', sa.Uuid(), nullable=False),
    sa.Column('global_product_presentation_id', sa.Uuid(), nullable=True),
    sa.Column('identifier_type', sa.String(length=30), nullable=False),
    sa.Column('value', sa.String(length=100), nullable=False),
    sa.Column('canonical_value', sa.String(length=100), nullable=False),
    sa.Column('is_primary', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_by', sa.String(length=255), nullable=False),
    sa.Column('updated_by', sa.String(length=255), nullable=False),
    sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.Column('status', sa.String(length=20), server_default=sa.text("'ACTIVE'"), nullable=False),
    sa.CheckConstraint("NOT is_primary OR status = 'ACTIVE'", name=op.f('ck_global_product_identifiers_primary_active')),
    sa.CheckConstraint("identifier_type IN ('GTIN','EAN','UPC','BARCODE','OTHER')", name=op.f('ck_global_product_identifiers_type')),
    sa.CheckConstraint("identifier_type NOT IN ('GTIN','EAN','UPC') OR (value ~ '^[0-9]+$' AND length(value) IN (8, 12, 13, 14) AND canonical_value = lpad(value, 14, '0'))", name=op.f('ck_global_product_identifiers_gtin_format')),
    sa.CheckConstraint("status IN ('ACTIVE','INACTIVE')", name=op.f('ck_global_product_identifiers_status')),
    sa.CheckConstraint("value !~ '[[:space:]-]' AND value <> ''", name=op.f('ck_global_product_identifiers_value_normalized')),
    sa.ForeignKeyConstraint(['global_product_id'], ['global_products.id'], name=op.f('fk_global_product_identifiers_global_product_id_global_products'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['global_product_presentation_id', 'global_product_id'], ['global_product_presentations.id', 'global_product_presentations.global_product_id'], name='fk_global_product_identifiers_presentation_product', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_global_product_identifiers'))
    )
    op.create_index('ix_global_product_identifiers_canonical_value', 'global_product_identifiers', ['canonical_value'], unique=False)
    op.create_index('uq_global_product_identifiers_barcode', 'global_product_identifiers', ['value'], unique=True, postgresql_where=sa.text("identifier_type = 'BARCODE'"))
    op.create_index('uq_global_product_identifiers_gtin_family', 'global_product_identifiers', ['canonical_value'], unique=True, postgresql_where=sa.text("identifier_type IN ('GTIN','EAN','UPC')"))
    op.create_index('uq_global_product_identifiers_other', 'global_product_identifiers', ['global_product_id', 'value'], unique=True, postgresql_where=sa.text("identifier_type = 'OTHER'"))
    op.create_index('uq_global_product_identifiers_primary', 'global_product_identifiers', ['global_product_id', 'global_product_presentation_id', 'identifier_type'], unique=True, postgresql_nulls_not_distinct=True, postgresql_where=sa.text("is_primary AND status = 'ACTIVE'"))


def downgrade() -> None:
    """Elimina las 16 tablas del catálogo global y la extensión pg_trgm."""
    op.drop_index('uq_global_product_identifiers_primary', table_name='global_product_identifiers', postgresql_nulls_not_distinct=True, postgresql_where=sa.text("is_primary AND status = 'ACTIVE'"))
    op.drop_index('uq_global_product_identifiers_other', table_name='global_product_identifiers', postgresql_where=sa.text("identifier_type = 'OTHER'"))
    op.drop_index('uq_global_product_identifiers_gtin_family', table_name='global_product_identifiers', postgresql_where=sa.text("identifier_type IN ('GTIN','EAN','UPC')"))
    op.drop_index('uq_global_product_identifiers_barcode', table_name='global_product_identifiers', postgresql_where=sa.text("identifier_type = 'BARCODE'"))
    op.drop_index('ix_global_product_identifiers_canonical_value', table_name='global_product_identifiers')
    op.drop_table('global_product_identifiers')
    op.drop_index('ix_global_product_attribute_values_attribute_definition_id', table_name='global_product_attribute_values')
    op.drop_table('global_product_attribute_values')
    op.drop_table('product_attribute_options')
    op.drop_index('uq_product_assets_primary', table_name='product_assets', postgresql_where=sa.text("is_primary AND status = 'ACTIVE'"))
    op.drop_index('ix_product_assets_global_product_id', table_name='product_assets')
    op.drop_table('product_assets')
    op.drop_index('uq_global_product_presentations_base', table_name='global_product_presentations', postgresql_where=sa.text("is_base AND status = 'ACTIVE'"))
    op.drop_table('global_product_presentations')
    op.drop_index('ix_global_product_group_assignments_product_type', table_name='global_product_group_assignments', postgresql_where=sa.text("status = 'ACTIVE'"))
    op.drop_index('ix_global_product_group_assignments_group_id', table_name='global_product_group_assignments')
    op.drop_table('global_product_group_assignments')
    op.drop_index('uq_global_product_categories_primary', table_name='global_product_categories', postgresql_where=sa.text("is_primary AND status = 'ACTIVE'"))
    op.drop_index('ix_global_product_categories_global_category_id', table_name='global_product_categories')
    op.drop_table('global_product_categories')
    op.drop_index('ix_global_category_attributes_attribute_definition_id', table_name='global_category_attributes')
    op.drop_table('global_category_attributes')
    op.drop_table('product_attribute_definitions')
    op.drop_index('ix_global_products_status', table_name='global_products')
    op.drop_index('ix_global_products_manufacturer_organization_id', table_name='global_products')
    op.drop_index('ix_global_products_global_brand_id', table_name='global_products')
    op.drop_index('ix_global_products_duplicate_key', table_name='global_products')
    op.drop_index('ix_global_products_canonical_name_key_trgm', table_name='global_products', postgresql_using='gin', postgresql_ops={'canonical_name_key': 'gin_trgm_ops'})
    op.drop_index('ix_global_products_base_unit_id', table_name='global_products')
    op.drop_table('global_products')
    op.drop_index('ix_global_product_groups_parent_group_id', table_name='global_product_groups')
    op.drop_table('global_product_groups')
    op.drop_table('global_units_of_measure')
    op.drop_table('global_product_group_types')
    op.drop_table('global_packaging_types')
    op.drop_index('ix_global_categories_parent_category_id', table_name='global_categories')
    op.drop_table('global_categories')
    op.drop_table('global_brands')
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
