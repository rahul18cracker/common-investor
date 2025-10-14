"""Extend schema with financial statements, metrics, valuations, and alerts.

Adds:
- fact table for XBRL tag storage
- statement_bs (balance sheet), statement_cf (cash flow)
- Extended statement_is with additional income statement fields
- metrics_yearly for computed financial ratios (ROIC, CAGR, etc.)
- valuation_scenario for Rule #1 valuation calculations
- meaning_note for Four Ms analysis notes
- alert_rule for price/metric alerts
- price_snapshot for historical price tracking

Revision ID: 0002_extend_schema
Revises: 0001_init
Create Date: 2024
"""
from alembic import op
import sqlalchemy as sa

revision = '0002_extend_schema'
down_revision = '0001_init'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('fact',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('filing_id', sa.Integer, sa.ForeignKey('filing.id')),
        sa.Column('statement', sa.Text),
        sa.Column('tag', sa.Text),
        sa.Column('fy', sa.Integer),
        sa.Column('fp', sa.Text),
        sa.Column('unit', sa.Text),
        sa.Column('value', sa.Numeric),
        sa.Column('decimals', sa.Integer),
        sa.Column('xbrl_path', sa.Text)
    )

    for col in ['cogs','gross_profit','sga','rnd','depreciation','ebit','interest_expense','taxes','net_income','shares_diluted']:
        op.add_column('statement_is', sa.Column(col, sa.Numeric, nullable=True))

    op.create_table('statement_bs',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('filing_id', sa.Integer, sa.ForeignKey('filing.id')),
        sa.Column('fy', sa.Integer),
        sa.Column('cash', sa.Numeric, nullable=True),
        sa.Column('receivables', sa.Numeric, nullable=True),
        sa.Column('inventory', sa.Numeric, nullable=True),
        sa.Column('total_assets', sa.Numeric, nullable=True),
        sa.Column('total_liabilities', sa.Numeric, nullable=True),
        sa.Column('total_debt', sa.Numeric, nullable=True),
        sa.Column('shareholder_equity', sa.Numeric, nullable=True)
    )

    op.create_table('statement_cf',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('filing_id', sa.Integer, sa.ForeignKey('filing.id')),
        sa.Column('fy', sa.Integer),
        sa.Column('cfo', sa.Numeric, nullable=True),
        sa.Column('capex', sa.Numeric, nullable=True),
        sa.Column('buybacks', sa.Numeric, nullable=True),
        sa.Column('dividends', sa.Numeric, nullable=True),
        sa.Column('acquisitions', sa.Numeric, nullable=True)
    )

    op.create_table('metrics_yearly',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('company_id', sa.Integer, sa.ForeignKey('company.id')),
        sa.Column('fy', sa.Integer),
        sa.Column('roic', sa.Numeric, nullable=True),
        sa.Column('rev_cagr_5y', sa.Numeric, nullable=True),
        sa.Column('eps_cagr_5y', sa.Numeric, nullable=True),
        sa.Column('owner_earnings', sa.Numeric, nullable=True),
        sa.Column('coverage', sa.Numeric, nullable=True),
        sa.Column('net_debt', sa.Numeric, nullable=True),
        sa.Column('debt_equity', sa.Numeric, nullable=True)
    )

    op.create_table('valuation_scenario',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('company_id', sa.Integer, sa.ForeignKey('company.id')),
        sa.Column('ts', sa.TIMESTAMP, server_default=sa.text('NOW()')),
        sa.Column('eps0', sa.Numeric, nullable=True),
        sa.Column('g', sa.Numeric, nullable=True),
        sa.Column('pe_cap', sa.Numeric, nullable=True),
        sa.Column('r', sa.Numeric, nullable=True),
        sa.Column('sticker', sa.Numeric, nullable=True),
        sa.Column('mos_pct', sa.Numeric, nullable=True),
        sa.Column('mos_price', sa.Numeric, nullable=True),
        sa.Column('owner_earnings0', sa.Numeric, nullable=True),
        sa.Column('payback_years', sa.Integer, nullable=True),
        sa.Column('ten_cap_ps', sa.Numeric, nullable=True),
        sa.Column('strategy', sa.Text, nullable=True)
    )

    op.create_table('meaning_note',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('company_id', sa.Integer, sa.ForeignKey('company.id')),
        sa.Column('ts', sa.TIMESTAMP, server_default=sa.text('NOW()')),
        sa.Column('text', sa.Text),
        sa.Column('source_url', sa.Text),
        sa.Column('section', sa.Text),
        sa.Column('evidence_type', sa.Text)
    )

    op.create_table('alert_rule',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('user_id', sa.Integer, nullable=True),
        sa.Column('company_id', sa.Integer, sa.ForeignKey('company.id')),
        sa.Column('rule_type', sa.Text),
        sa.Column('threshold', sa.Numeric, nullable=True),
        sa.Column('enabled', sa.Boolean, server_default=sa.text('true')),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP, server_default=sa.text('NOW()'))
    )

    op.create_table('price_snapshot',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('company_id', sa.Integer, sa.ForeignKey('company.id')),
        sa.Column('ts', sa.TIMESTAMP, server_default=sa.text('NOW()')),
        sa.Column('price', sa.Numeric),
        sa.Column('source', sa.Text),
        sa.Column('currency', sa.Text)
    )

def downgrade():
    op.drop_table('price_snapshot')
    op.drop_table('alert_rule')
    op.drop_table('meaning_note')
    op.drop_table('valuation_scenario')
    op.drop_table('metrics_yearly')
    op.drop_table('statement_cf')
    op.drop_table('statement_bs')
    op.drop_table('fact')