"""Add SIC code and fiscal year end month to company table.

Phase 1B: industry classification + Phase 1C: fiscal year end month.

Revision ID: 0003_add_sic_and_fiscal_year_end
Revises: 0002_extend_schema
Create Date: 2026-04-07
"""
from alembic import op
import sqlalchemy as sa

revision = '0003_add_sic_and_fiscal_year_end'
down_revision = '0002_extend_schema'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('company', sa.Column('sic_code', sa.Text, nullable=True))
    op.add_column('company', sa.Column('fiscal_year_end_month', sa.Integer, nullable=True))


def downgrade():
    op.drop_column('company', 'fiscal_year_end_month')
    op.drop_column('company', 'sic_code')
