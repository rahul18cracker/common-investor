"""Initial database schema for Common Investor application.

Creates core tables:
- company: Company master data (CIK, ticker, name, sector, industry)
- filing: SEC filings metadata (form type, accession, period)
- statement_is: Income statement data (revenue, EPS)

Revision ID: 0001_init
Revises: None
Create Date: 2024
"""
from alembic import op
import sqlalchemy as sa

revision = '0001_init'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('company',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('cik', sa.Text, unique=True, nullable=False),
        sa.Column('ticker', sa.Text, unique=True, nullable=False),
        sa.Column('name', sa.Text),
        sa.Column('sector', sa.Text),
        sa.Column('industry', sa.Text),
        sa.Column('currency', sa.Text)
    )
    op.create_table('filing',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('cik', sa.Text, nullable=False),
        sa.Column('form', sa.Text),
        sa.Column('accession', sa.Text, unique=True),
        sa.Column('period_end', sa.Date),
        sa.Column('accepted_at', sa.TIMESTAMP),
        sa.Column('source_url', sa.Text),
        sa.Column('checksum', sa.Text)
    )
    op.create_table('statement_is',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('filing_id', sa.Integer, sa.ForeignKey('filing.id')),
        sa.Column('fy', sa.Integer),
        sa.Column('revenue', sa.Numeric, nullable=True),
        sa.Column('eps_diluted', sa.Numeric, nullable=True)
    )

def downgrade():
    op.drop_table('statement_is')
    op.drop_table('filing')
    op.drop_table('company')