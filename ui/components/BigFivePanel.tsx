'use client';
import { useEffect, useState } from 'react';

// Helper to get status color and label based on value vs target
function getMetricStatus(
  value: number | null | undefined,
  target: number,
  higherIsBetter = true
): { color: string; label: string; bg: string; icon: string } {
  if (value === null || value === undefined) {
    return { color: '#6b7280', label: 'No Data', bg: '#f3f4f6', icon: '—' };
  }
  
  const ratio = higherIsBetter ? value / target : target / value;
  
  if (ratio >= 1.2) return { color: '#15803d', label: 'Excellent', bg: '#dcfce7', icon: '✓' };
  if (ratio >= 1.0) return { color: '#65a30d', label: 'Good', bg: '#ecfccb', icon: '✓' };
  if (ratio >= 0.8) return { color: '#ca8a04', label: 'Fair', bg: '#fef9c3', icon: '~' };
  if (ratio >= 0.6) return { color: '#ea580c', label: 'Weak', bg: '#ffedd5', icon: '!' };
  return { color: '#dc2626', label: 'Poor', bg: '#fee2e2', icon: '✗' };
}

// Format percentage
function formatPct(value: number | null | undefined, decimals = 1): string {
  if (value === null || value === undefined) return 'N/A';
  return `${(value * 100).toFixed(decimals)}%`;
}

// Format currency (millions/billions)
function formatCurrency(value: number | null | undefined): string {
  if (value === null || value === undefined) return 'N/A';
  if (Math.abs(value) >= 1e9) return `$${(value / 1e9).toFixed(1)}B`;
  if (Math.abs(value) >= 1e6) return `$${(value / 1e6).toFixed(1)}M`;
  return `$${value.toFixed(0)}`;
}

// Info tooltip component
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

// Big Five metric card
function BigFiveCard({
  number,
  title,
  icon,
  description,
  value,
  formattedValue,
  target,
  targetLabel,
  higherIsBetter = true,
  trend,
  children
}: {
  number: number;
  title: string;
  icon: string;
  description: string;
  value: number | null | undefined;
  formattedValue: string;
  target: number;
  targetLabel: string;
  higherIsBetter?: boolean;
  trend?: { label: string; value: string };
  children?: React.ReactNode;
}) {
  const status = getMetricStatus(value, target, higherIsBetter);
  
  return (
    <div style={{
      border: '1px solid #e5e7eb',
      borderRadius: 12,
      padding: 20,
      background: '#fff',
      boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
      position: 'relative',
      overflow: 'hidden'
    }}>
      {/* Number badge */}
      <div style={{
        position: 'absolute',
        top: 12,
        right: 12,
        width: 28,
        height: 28,
        borderRadius: '50%',
        background: '#f3f4f6',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: 14,
        fontWeight: 700,
        color: '#6b7280'
      }}>
        {number}
      </div>
      
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
        <span style={{ fontSize: 28 }}>{icon}</span>
        <div>
          <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600, color: '#111' }}>{title}</h3>
          <InfoTip text={description} />
        </div>
      </div>
      
      {/* Main value */}
      <div style={{ marginBottom: 12 }}>
        <div style={{ fontSize: 36, fontWeight: 700, color: status.color }}>
          {formattedValue}
        </div>
        <div style={{ 
          display: 'inline-flex',
          alignItems: 'center',
          gap: 6,
          padding: '4px 10px',
          borderRadius: 12,
          background: status.bg,
          color: status.color,
          fontSize: 13,
          fontWeight: 600,
          marginTop: 4
        }}>
          <span>{status.icon}</span>
          <span>{status.label}</span>
        </div>
      </div>
      
      {/* Target */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '8px 12px',
        background: '#f9fafb',
        borderRadius: 6,
        marginBottom: 12
      }}>
        <span style={{ fontSize: 13, color: '#6b7280' }}>Target</span>
        <span style={{ fontSize: 13, fontWeight: 600, color: '#374151' }}>{targetLabel}</span>
      </div>
      
      {/* Trend if available */}
      {trend && (
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '8px 12px',
          background: '#f0f9ff',
          borderRadius: 6,
          marginBottom: 12
        }}>
          <span style={{ fontSize: 13, color: '#0369a1' }}>{trend.label}</span>
          <span style={{ fontSize: 13, fontWeight: 600, color: '#0369a1' }}>{trend.value}</span>
        </div>
      )}
      
      {/* Additional content */}
      {children}
    </div>
  );
}

interface BigFiveData {
  roic_avg?: number;
  rev_cagr_5y?: number;
  rev_cagr_10y?: number;
  eps_cagr_5y?: number;
  eps_cagr_10y?: number;
  owner_earnings?: number;
  fcf_latest?: number;
  debt_equity?: number;
  interest_coverage?: number;
}

export default function BigFivePanel({ api, ticker }: { api: string; ticker: string }) {
  const [metrics, setMetrics] = useState<BigFiveData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchMetrics() {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`${api}/api/v1/company/${ticker}/metrics`);
        if (!res.ok) throw new Error('Failed to fetch metrics');
        const data = await res.json();
        setMetrics(data);
      } catch (e: any) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    }
    fetchMetrics();
  }, [api, ticker]);

  if (loading) {
    return (
      <section style={{ marginTop: 32 }}>
        <h2 style={{ margin: 0, fontSize: 24, fontWeight: 700, color: '#111' }}>
          The Big Five Numbers
        </h2>
        <p style={{ color: '#6b7280', marginTop: 8 }}>Loading metrics...</p>
      </section>
    );
  }

  if (error) {
    return (
      <section style={{ marginTop: 32 }}>
        <h2 style={{ margin: 0, fontSize: 24, fontWeight: 700, color: '#111' }}>
          The Big Five Numbers
        </h2>
        <p style={{ color: '#dc2626', marginTop: 8 }}>Error: {error}</p>
      </section>
    );
  }

  // Calculate overall score
  const scores = [
    metrics?.roic_avg && metrics.roic_avg >= 0.15 ? 1 : 0,
    metrics?.rev_cagr_10y && metrics.rev_cagr_10y >= 0.10 ? 1 : 0,
    metrics?.eps_cagr_10y && metrics.eps_cagr_10y >= 0.10 ? 1 : 0,
    metrics?.fcf_latest && metrics.fcf_latest > 0 ? 1 : 0,
    metrics?.debt_equity !== undefined && metrics.debt_equity < 0.5 ? 1 : 0,
  ];
  const overallScore = scores.reduce((a, b) => a + b, 0);
  const overallColor = overallScore >= 4 ? '#15803d' : overallScore >= 3 ? '#65a30d' : overallScore >= 2 ? '#ca8a04' : '#dc2626';

  return (
    <section style={{ marginTop: 32 }}>
      {/* Header */}
      <div style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
          <div>
            <h2 style={{ margin: 0, fontSize: 24, fontWeight: 700, color: '#111' }}>
              The Big Five Numbers
            </h2>
            <p style={{ margin: '8px 0 0', color: '#6b7280', fontSize: 14 }}>
              Rule #1&apos;s key metrics to identify wonderful companies with predictable growth
            </p>
          </div>
          <div style={{
            padding: '12px 20px',
            background: overallColor,
            borderRadius: 12,
            color: '#fff',
            textAlign: 'center'
          }}>
            <div style={{ fontSize: 24, fontWeight: 700 }}>{overallScore}/5</div>
            <div style={{ fontSize: 12, opacity: 0.9 }}>Metrics Passing</div>
          </div>
        </div>
      </div>

      {/* Big Five Cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
        gap: 16
      }}>
        {/* 1. ROIC */}
        <BigFiveCard
          number={1}
          title="ROIC"
          icon="📊"
          description="Return on Invested Capital measures how efficiently management uses the company's capital to generate profits. Consistent high ROIC indicates a durable competitive advantage (moat)."
          value={metrics?.roic_avg}
          formattedValue={formatPct(metrics?.roic_avg)}
          target={0.15}
          targetLabel="≥15% (10-year avg)"
        >
          <p style={{ fontSize: 12, color: '#6b7280', margin: 0 }}>
            <strong>Why it matters:</strong> Companies with ROIC consistently above 15% have a moat that protects their profits.
          </p>
        </BigFiveCard>

        {/* 2. Revenue Growth */}
        <BigFiveCard
          number={2}
          title="Revenue Growth"
          icon="📈"
          description="Compound Annual Growth Rate (CAGR) of revenue shows how fast the company is growing its top line. Consistent growth indicates strong demand and market position."
          value={metrics?.rev_cagr_10y}
          formattedValue={formatPct(metrics?.rev_cagr_10y)}
          target={0.10}
          targetLabel="≥10% CAGR"
          trend={metrics?.rev_cagr_5y !== undefined ? {
            label: '5-Year CAGR',
            value: formatPct(metrics.rev_cagr_5y)
          } : undefined}
        >
          <p style={{ fontSize: 12, color: '#6b7280', margin: 0 }}>
            <strong>Why it matters:</strong> Predictable revenue growth means the business is expanding its market or raising prices.
          </p>
        </BigFiveCard>

        {/* 3. EPS Growth */}
        <BigFiveCard
          number={3}
          title="EPS Growth"
          icon="💰"
          description="Earnings Per Share growth shows how fast profits available to shareholders are growing. This is the key driver of stock price over time."
          value={metrics?.eps_cagr_10y}
          formattedValue={formatPct(metrics?.eps_cagr_10y)}
          target={0.10}
          targetLabel="≥10% CAGR"
          trend={metrics?.eps_cagr_5y !== undefined ? {
            label: '5-Year CAGR',
            value: formatPct(metrics.eps_cagr_5y)
          } : undefined}
        >
          <p style={{ fontSize: 12, color: '#6b7280', margin: 0 }}>
            <strong>Why it matters:</strong> EPS growth drives stock price. Consistent growth = predictable future value.
          </p>
        </BigFiveCard>

        {/* 4. Free Cash Flow / Owner Earnings */}
        <BigFiveCard
          number={4}
          title="Free Cash Flow"
          icon="💵"
          description="Owner Earnings (Operating Cash Flow minus CapEx) represents the actual cash the business generates for owners after maintaining the business."
          value={metrics?.fcf_latest}
          formattedValue={metrics?.fcf_latest !== undefined ? formatCurrency(metrics.fcf_latest) : 'N/A'}
          target={1}
          targetLabel="Positive & Growing"
        >
          <p style={{ fontSize: 12, color: '#6b7280', margin: 0 }}>
            <strong>Why it matters:</strong> Cash is king. Positive FCF means the company can pay dividends, buy back stock, or reinvest.
          </p>
        </BigFiveCard>

        {/* 5. Debt & Solvency */}
        <BigFiveCard
          number={5}
          title="Debt Level"
          icon="🏦"
          description="Debt-to-Equity ratio shows how much the company relies on borrowed money. Lower debt means less risk and more flexibility."
          value={metrics?.debt_equity}
          formattedValue={metrics?.debt_equity !== undefined ? `${(metrics.debt_equity).toFixed(2)}` : 'N/A'}
          target={0.5}
          targetLabel="<50% D/E Ratio"
          higherIsBetter={false}
          trend={metrics?.interest_coverage !== undefined ? {
            label: 'Interest Coverage',
            value: `${metrics.interest_coverage.toFixed(1)}x`
          } : undefined}
        >
          <p style={{ fontSize: 12, color: '#6b7280', margin: 0 }}>
            <strong>Why it matters:</strong> Low debt = less risk. The company can survive downturns and doesn&apos;t need to dilute shareholders.
          </p>
        </BigFiveCard>
      </div>

      {/* Educational Summary */}
      <div style={{
        marginTop: 20,
        padding: 20,
        background: '#f0f9ff',
        border: '1px solid #bae6fd',
        borderRadius: 12
      }}>
        <h4 style={{ margin: '0 0 12px', color: '#0369a1' }}>Understanding the Big Five</h4>
        <p style={{ margin: 0, fontSize: 14, color: '#0c4a6e', lineHeight: 1.6 }}>
          Phil Town&apos;s Rule #1 methodology looks for companies where all five numbers show{' '}
          <strong>consistent growth of at least 10% per year</strong> over the past 10 years.
          A company that passes all five tests is likely a &quot;wonderful company&quot; with a durable competitive advantage.
          The more metrics that pass, the more predictable the business — and the easier it is to value accurately.
        </p>
      </div>
    </section>
  );
}
