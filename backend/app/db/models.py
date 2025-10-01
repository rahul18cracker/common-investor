from __future__ import annotations
from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from sqlalchemy import Integer, Text, Date, DateTime, Boolean, Numeric, ForeignKey

Base = declarative_base()

class Company(Base):
    __tablename__ = "company"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cik: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    ticker: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(Text)
    sector: Mapped[str | None] = mapped_column(Text)
    industry: Mapped[str | None] = mapped_column(Text)
    currency: Mapped[str | None] = mapped_column(Text)

class Filing(Base):
    __tablename__ = "filing"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cik: Mapped[str] = mapped_column(Text, nullable=False)
    form: Mapped[str | None] = mapped_column(Text)
    accession: Mapped[str | None] = mapped_column(Text, unique=True)
    period_end: Mapped[Date | None] = mapped_column(Date)
    accepted_at: Mapped[DateTime | None] = mapped_column(DateTime)
    source_url: Mapped[str | None] = mapped_column(Text)
    checksum: Mapped[str | None] = mapped_column(Text)

class StatementIS(Base):
    __tablename__ = "statement_is"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filing_id: Mapped[int | None] = mapped_column(ForeignKey("filing.id"))
    fy: Mapped[int | None] = mapped_column(Integer)
    revenue: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    cogs: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    gross_profit: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    sga: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    rnd: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    depreciation: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    ebit: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    interest_expense: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    taxes: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    net_income: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    eps_diluted: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    shares_diluted: Mapped[float | None] = mapped_column(Numeric, nullable=True)

class StatementBS(Base):
    __tablename__ = "statement_bs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filing_id: Mapped[int | None] = mapped_column(ForeignKey("filing.id"))
    fy: Mapped[int | None] = mapped_column(Integer)
    cash: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    receivables: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    inventory: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    total_assets: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    total_liabilities: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    total_debt: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    shareholder_equity: Mapped[float | None] = mapped_column(Numeric, nullable=True)

class StatementCF(Base):
    __tablename__ = "statement_cf"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filing_id: Mapped[int | None] = mapped_column(ForeignKey("filing.id"))
    fy: Mapped[int | None] = mapped_column(Integer)
    cfo: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    capex: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    buybacks: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    dividends: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    acquisitions: Mapped[float | None] = mapped_column(Numeric, nullable=True)

class MetricsYearly(Base):
    __tablename__ = "metrics_yearly"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("company.id"))
    fy: Mapped[int | None] = mapped_column(Integer)
    roic: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    rev_cagr_5y: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    eps_cagr_5y: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    owner_earnings: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    coverage: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    net_debt: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    debt_equity: Mapped[float | None] = mapped_column(Numeric, nullable=True)

class ValuationScenario(Base):
    __tablename__ = "valuation_scenario"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("company.id"))
    ts: Mapped[DateTime] = mapped_column(DateTime)
    eps0: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    g: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    pe_cap: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    r: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    sticker: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    mos_pct: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    mos_price: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    owner_earnings0: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    payback_years: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ten_cap_ps: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    strategy: Mapped[str | None] = mapped_column(Text, nullable=True)

class MeaningNote(Base):
    __tablename__ = "meaning_note"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("company.id"))
    ts: Mapped[DateTime] = mapped_column(DateTime)
    text: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text)
    section: Mapped[str | None] = mapped_column(Text)
    evidence_type: Mapped[str | None] = mapped_column(Text)

class AlertRule(Base):
    __tablename__ = "alert_rule"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("company.id"))
    rule_type: Mapped[str] = mapped_column(Text)
    threshold: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

class PriceSnapshot(Base):
    __tablename__ = "price_snapshot"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("company.id"))
    ts: Mapped[DateTime] = mapped_column(DateTime)
    price: Mapped[float] = mapped_column(Numeric)
    source: Mapped[str | None] = mapped_column(Text)
    currency: Mapped[str | None] = mapped_column(Text)