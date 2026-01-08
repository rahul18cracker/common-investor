'use client';
import { useEffect, useState } from 'react';

function formatCurrency(value: number | null | undefined): string {
  if (value === null || value === undefined) return 'N/A';
  if (Math.abs(value) >= 1e9) return `$${(value / 1e9).toFixed(1)}B`;
  if (Math.abs(value) >= 1e6) return `$${(value / 1e6).toFixed(1)}M`;
  return `$${value.toFixed(0)}`;
}

function formatPct(value: number | null | undefined, decimals = 1): string {
  if (value === null || value === undefined) return 'N/A';
  return `${(value * 100).toFixed(decimals)}%`;
}

function getMarginStatus(value: number | null | undefined, target: number): { color: string; bg: string } {
  if (value === null || value === undefined) {
    return { color: '#6b7280', bg: '#f3f4f6' };
  }
  if (value >= target * 1.2) return { color: '#15803d', bg: '#dcfce7' };
  if (value >= target) return { color: '#65a30d', bg: '#ecfccb' };
  if (value >= target * 0.8) return { color: '#ca8a04', bg: '#fef9c3' };
  return { color: '#dc2626', bg: '#fee2e2' };
}

function InfoTip({ text }: { text: string }) {
  return (
    <span 
      title={text}
      style={{ 
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        width: 16, 
        height: 16, 
        borderRadius: '50%', 
        background: '#e5e7eb', 
        color: '#666',
        fontSize: 11,
        fontWeight: 600,
        marginLeft: 6,
        cursor: 'help'
      }}
    >
      ?
    </span>
  );
}

interface IncomeStatementData {
  fy?: number;
  revenue?: number;
  cogs?: number;
  gross_profit?: number;
  sga?: number;
  rnd?: number;
  depreciation?: number;
  ebit?: number;
  interest_expense?: number;
  taxes?: number;
  net_income?: number;
  eps_diluted?: number;
  shares_diluted?: number;
  gross_margin?: number;
  operating_margin?: number;
}

export default function IncomeStatementPanel({ api, ticker }: { api: string; ticker: string }) {
  const [data, setData] = useState<IncomeStatementData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`${api}/api/v1/company/${ticker}`);
        if (!res.ok) throw new Error('Failed to fetch company data');
        const json = await res.json();
        setData(json.latest_is);
      } catch (e: any) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, [api, ticker]);

  if (loading) {
    return (
      <section style={{ marginTop: 32 }}>
        <h2 style={{ margin: 0, fontSize: 24, fontWeight: 700, color: '#111' }}>
          Income Statement Breakdown
        </h2>
        <p style={{ color: '#6b7280', marginTop: 8 }}>Loading...</p>
      </section>
    );
  }

  if (error || !data) {
    return (
      <section style={{ marginTop: 32 }}>
        <h2 style={{ margin: 0, fontSize: 24, fontWeight: 700, color: '#111' }}>
          Income Statement Breakdown
        </h2>
        <p style={{ color: '#9ca3af', marginTop: 8 }}>
          {error || 'No income statement data available. Click "Ingest SEC Data" to fetch financial data.'}
        </p>
      </section>
    );
  }

  const grossMarginStatus = getMarginStatus(data.gross_margin, 0.40);
  const operatingMarginStatus = getMarginStatus(data.operating_margin, 0.20);

  return (
    <section style={{ marginTop: 32 }}>
      <div style={{ marginBottom: 20 }}>
        <h2 style={{ margin: 0, fontSize: 24, fontWeight: 700, color: '#111' }}>
          Income Statement Breakdown
        </h2>
        <p style={{ margin: '8px 0 0', color: '#6b7280', fontSize: 14 }}>
          FY{data.fy} - Detailed breakdown of revenue, costs, and profitability
        </p>
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
        gap: 20
      }}>
        {/* Margin Highlights */}
        <div style={{
          border: '1px solid #e5e7eb',
          borderRadius: 12,
          padding: 20,
          background: '#fff',
          boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
        }}>
          <h3 style={{ margin: '0 0 16px', fontSize: 18, fontWeight: 600, color: '#111' }}>
            Profitability Margins
            <InfoTip text="Margins show how much profit the company keeps at each stage. Higher margins indicate pricing power and efficiency." />
          </h3>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {/* Gross Margin */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                <span style={{ fontSize: 14, color: '#374151' }}>Gross Margin</span>
                <span style={{ 
                  fontSize: 20, 
                  fontWeight: 700, 
                  color: grossMarginStatus.color 
                }}>
                  {formatPct(data.gross_margin)}
                </span>
              </div>
              <div style={{
                height: 8,
                background: '#f3f4f6',
                borderRadius: 4,
                overflow: 'hidden'
              }}>
                <div style={{
                  height: '100%',
                  width: `${Math.min((data.gross_margin || 0) * 100, 100)}%`,
                  background: grossMarginStatus.color,
                  borderRadius: 4,
                  transition: 'width 0.3s ease'
                }} />
              </div>
              <p style={{ margin: '4px 0 0', fontSize: 12, color: '#6b7280' }}>
                Target: ≥40% indicates pricing power
              </p>
            </div>

            {/* Operating Margin */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                <span style={{ fontSize: 14, color: '#374151' }}>Operating Margin</span>
                <span style={{ 
                  fontSize: 20, 
                  fontWeight: 700, 
                  color: operatingMarginStatus.color 
                }}>
                  {formatPct(data.operating_margin)}
                </span>
              </div>
              <div style={{
                height: 8,
                background: '#f3f4f6',
                borderRadius: 4,
                overflow: 'hidden'
              }}>
                <div style={{
                  height: '100%',
                  width: `${Math.min((data.operating_margin || 0) * 100, 100)}%`,
                  background: operatingMarginStatus.color,
                  borderRadius: 4,
                  transition: 'width 0.3s ease'
                }} />
              </div>
              <p style={{ margin: '4px 0 0', fontSize: 12, color: '#6b7280' }}>
                Target: ≥20% indicates operational efficiency
              </p>
            </div>

            {/* Net Margin */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                <span style={{ fontSize: 14, color: '#374151' }}>Net Margin</span>
                <span style={{ fontSize: 20, fontWeight: 700, color: '#374151' }}>
                  {data.revenue && data.net_income 
                    ? formatPct(data.net_income / data.revenue) 
                    : 'N/A'}
                </span>
              </div>
              <p style={{ margin: '4px 0 0', fontSize: 12, color: '#6b7280' }}>
                Bottom-line profitability after all expenses
              </p>
            </div>
          </div>
        </div>

        {/* Income Statement Waterfall */}
        <div style={{
          border: '1px solid #e5e7eb',
          borderRadius: 12,
          padding: 20,
          background: '#fff',
          boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
        }}>
          <h3 style={{ margin: '0 0 16px', fontSize: 18, fontWeight: 600, color: '#111' }}>
            Income Statement Flow
            <InfoTip text="Shows how revenue flows down to net income through various costs and expenses." />
          </h3>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid #f3f4f6' }}>
              <span style={{ fontWeight: 600, color: '#111' }}>Revenue</span>
              <span style={{ fontWeight: 600, color: '#2563eb' }}>{formatCurrency(data.revenue)}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', paddingLeft: 16, borderBottom: '1px solid #f3f4f6' }}>
              <span style={{ color: '#dc2626' }}>− Cost of Revenue (COGS)</span>
              <span style={{ color: '#dc2626' }}>{formatCurrency(data.cogs)}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', background: '#f0fdf4', borderRadius: 4 }}>
              <span style={{ fontWeight: 600, color: '#15803d' }}>= Gross Profit</span>
              <span style={{ fontWeight: 600, color: '#15803d' }}>{formatCurrency(data.gross_profit)}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', paddingLeft: 16, borderBottom: '1px solid #f3f4f6' }}>
              <span style={{ color: '#dc2626' }}>− SG&A Expenses</span>
              <span style={{ color: '#dc2626' }}>{formatCurrency(data.sga)}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', paddingLeft: 16, borderBottom: '1px solid #f3f4f6' }}>
              <span style={{ color: '#dc2626' }}>− R&D Expenses</span>
              <span style={{ color: '#dc2626' }}>{formatCurrency(data.rnd)}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', paddingLeft: 16, borderBottom: '1px solid #f3f4f6' }}>
              <span style={{ color: '#dc2626' }}>− Depreciation & Amortization</span>
              <span style={{ color: '#dc2626' }}>{formatCurrency(data.depreciation)}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', background: '#eff6ff', borderRadius: 4 }}>
              <span style={{ fontWeight: 600, color: '#1d4ed8' }}>= Operating Income (EBIT)</span>
              <span style={{ fontWeight: 600, color: '#1d4ed8' }}>{formatCurrency(data.ebit)}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', paddingLeft: 16, borderBottom: '1px solid #f3f4f6' }}>
              <span style={{ color: '#dc2626' }}>− Interest Expense</span>
              <span style={{ color: '#dc2626' }}>{formatCurrency(data.interest_expense)}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', paddingLeft: 16, borderBottom: '1px solid #f3f4f6' }}>
              <span style={{ color: '#dc2626' }}>− Taxes</span>
              <span style={{ color: '#dc2626' }}>{formatCurrency(data.taxes)}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', background: '#faf5ff', borderRadius: 4 }}>
              <span style={{ fontWeight: 600, color: '#7c3aed' }}>= Net Income</span>
              <span style={{ fontWeight: 600, color: '#7c3aed' }}>{formatCurrency(data.net_income)}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Educational Note */}
      <div style={{
        marginTop: 20,
        padding: 16,
        background: '#f0f9ff',
        border: '1px solid #bae6fd',
        borderRadius: 8
      }}>
        <p style={{ margin: 0, fontSize: 13, color: '#0c4a6e' }}>
          <strong>Why margins matter:</strong> High gross margins indicate pricing power and competitive advantage. 
          Consistent operating margins show management efficiency. Companies with expanding margins over time 
          often have durable moats that protect their profitability.
        </p>
      </div>
    </section>
  );
}
