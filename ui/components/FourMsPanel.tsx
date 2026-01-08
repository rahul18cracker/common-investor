'use client';
import { useState } from 'react';

// Helper to get score color and label (0-1 scale)
function getScoreInfo(score: number | null | undefined): { color: string; label: string; bg: string } {
  if (score === null || score === undefined) return { color: '#666', label: 'Unknown', bg: '#f0f0f0' };
  if (score >= 0.8) return { color: '#15803d', label: 'Excellent', bg: '#dcfce7' };
  if (score >= 0.6) return { color: '#65a30d', label: 'Good', bg: '#ecfccb' };
  if (score >= 0.4) return { color: '#ca8a04', label: 'Fair', bg: '#fef9c3' };
  if (score >= 0.2) return { color: '#ea580c', label: 'Weak', bg: '#ffedd5' };
  return { color: '#dc2626', label: 'Poor', bg: '#fee2e2' };
}

// Helper to get score color and label (0-5 scale) - Phase E
function getScore5Info(score: number | null | undefined): { color: string; label: string; bg: string } {
  if (score === null || score === undefined) return { color: '#666', label: 'N/A', bg: '#f0f0f0' };
  if (score >= 4) return { color: '#15803d', label: 'Excellent', bg: '#dcfce7' };
  if (score >= 3) return { color: '#65a30d', label: 'Good', bg: '#ecfccb' };
  if (score >= 2) return { color: '#ca8a04', label: 'Fair', bg: '#fef9c3' };
  if (score >= 1) return { color: '#ea580c', label: 'Weak', bg: '#ffedd5' };
  return { color: '#dc2626', label: 'Poor', bg: '#fee2e2' };
}

// E2: ROIC Persistence Badge Component
function PersistenceBadge({ score }: { score: number | null | undefined }) {
  const info = getScore5Info(score);
  return (
    <div style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: 6,
      padding: '6px 12px',
      borderRadius: 20,
      background: info.bg,
      border: `1px solid ${info.color}20`
    }}>
      <span style={{ fontSize: 18 }}>
        {score !== null && score !== undefined ? '⭐'.repeat(Math.min(5, Math.max(0, Math.round(score)))) : '—'}
      </span>
      <span style={{ fontSize: 13, fontWeight: 600, color: info.color }}>
        {score !== null && score !== undefined ? `${score}/5` : 'N/A'}
      </span>
    </div>
  );
}

// E4: Volatility Indicator Component
function VolatilityIndicator({ volatility }: { volatility: number | null | undefined }) {
  if (volatility === null || volatility === undefined) {
    return <span style={{ color: '#666' }}>N/A</span>;
  }
  
  let level: string;
  let color: string;
  let icon: string;
  
  if (volatility <= 0.10) {
    level = 'Low';
    color = '#15803d';
    icon = '📊';
  } else if (volatility <= 0.20) {
    level = 'Moderate';
    color = '#ca8a04';
    icon = '📈';
  } else {
    level = 'High';
    color = '#dc2626';
    icon = '🎢';
  }
  
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <span>{icon}</span>
      <span style={{ fontWeight: 600, color }}>{level}</span>
      <span style={{ fontSize: 12, color: '#666' }}>({(volatility * 100).toFixed(1)}%)</span>
    </div>
  );
}

// Helper to format percentage
function formatPct(value: number | null | undefined, decimals = 1): string {
  if (value === null || value === undefined) return 'N/A';
  return `${(value * 100).toFixed(decimals)}%`;
}

// Progress bar component
function ScoreBar({ score, label }: { score: number | null | undefined; label: string }) {
  const info = getScoreInfo(score);
  const pct = score !== null && score !== undefined ? Math.round(score * 100) : 0;
  
  return (
    <div style={{ marginTop: 8 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
        <span style={{ fontSize: 13, color: '#555' }}>{label}</span>
        <span style={{ fontSize: 13, fontWeight: 600, color: info.color }}>{info.label}</span>
      </div>
      <div style={{ height: 8, background: '#e5e7eb', borderRadius: 4, overflow: 'hidden' }}>
        <div 
          style={{ 
            height: '100%', 
            width: `${pct}%`, 
            background: info.color,
            borderRadius: 4,
            transition: 'width 0.3s ease'
          }} 
        />
      </div>
    </div>
  );
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

// Card component for each M
function MCard({ 
  title, 
  icon, 
  description, 
  children, 
  score 
}: { 
  title: string; 
  icon: string; 
  description: string; 
  children: React.ReactNode;
  score?: number | null;
}) {
  const info = getScoreInfo(score);
  
  return (
    <div style={{ 
      border: '1px solid #e5e7eb', 
      borderRadius: 12, 
      padding: 16,
      background: '#fff',
      boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
        <span style={{ fontSize: 24 }}>{icon}</span>
        <h3 style={{ margin: 0, fontSize: 18, fontWeight: 600 }}>{title}</h3>
        <InfoTip text={description} />
      </div>
      {score !== undefined && (
        <div style={{ 
          display: 'inline-block',
          padding: '4px 10px', 
          borderRadius: 12, 
          background: info.bg,
          color: info.color,
          fontSize: 13,
          fontWeight: 600,
          marginBottom: 12
        }}>
          Score: {score !== null ? `${Math.round(score * 100)}/100` : 'N/A'} — {info.label}
        </div>
      )}
      {children}
    </div>
  );
}

// Metric row component
function MetricRow({ 
  label, 
  value, 
  hint, 
  target 
}: { 
  label: string; 
  value: string; 
  hint?: string;
  target?: string;
}) {
  return (
    <div style={{ 
      display: 'flex', 
      justifyContent: 'space-between', 
      alignItems: 'center',
      padding: '8px 0',
      borderBottom: '1px solid #f3f4f6'
    }}>
      <div>
        <span style={{ fontSize: 14, color: '#374151' }}>{label}</span>
        {hint && <InfoTip text={hint} />}
      </div>
      <div style={{ textAlign: 'right' }}>
        <span style={{ fontSize: 14, fontWeight: 600, color: '#111' }}>{value}</span>
        {target && <div style={{ fontSize: 11, color: '#6b7280' }}>Target: {target}</div>}
      </div>
    </div>
  );
}

export default function FourMsPanel({ api, ticker }: { api: string; ticker: string }) {
  const [data, setData] = useState<any>(null);
  const [meaning, setMeaning] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [meaningLoading, setMeaningLoading] = useState(false);

  async function loadSummary() {
    setLoading(true);
    try {
      const res = await fetch(`${api}/api/v1/company/${ticker}/fourm`);
      setData(await res.json());
    } finally {
      setLoading(false);
    }
  }

  async function refreshMeaning() {
    setMeaningLoading(true);
    try {
      const res = await fetch(`${api}/api/v1/company/${ticker}/fourm/meaning/refresh`, { method: 'POST' });
      const j = await res.json();
      setMeaning(j.item1_excerpt || '');
    } finally {
      setMeaningLoading(false);
    }
  }

  const mosPercent = data?.mos_recommendation?.recommended_mos;
  const mosInfo = mosPercent !== undefined ? (
    mosPercent >= 0.5 ? { color: '#dc2626', label: 'High Risk - Requires large discount' } :
    mosPercent >= 0.4 ? { color: '#ea580c', label: 'Moderate Risk - Be cautious' } :
    mosPercent >= 0.3 ? { color: '#ca8a04', label: 'Average Risk - Standard buffer' } :
    { color: '#15803d', label: 'Lower Risk - Strong fundamentals' }
  ) : { color: '#666', label: '' };

  return (
    <section style={{ marginTop: 32 }}>
      {/* Header */}
      <div style={{ marginBottom: 16 }}>
        <h2 style={{ margin: 0, fontSize: 24, fontWeight: 700, color: '#111' }}>
          The Four Ms Analysis
        </h2>
        <p style={{ margin: '8px 0 0', color: '#6b7280', fontSize: 14 }}>
          Phil Town&apos;s Rule #1 framework for evaluating wonderful companies at attractive prices
        </p>
      </div>

      {/* Action Buttons */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 20 }}>
        <button 
          onClick={loadSummary}
          disabled={loading}
          style={{
            padding: '10px 20px',
            background: loading ? '#9ca3af' : '#2563eb',
            color: '#fff',
            border: 'none',
            borderRadius: 8,
            fontWeight: 600,
            cursor: loading ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: 8
          }}
        >
          {loading ? 'Analyzing...' : 'Analyze Moat, Management & MOS'}
        </button>
        <button 
          onClick={refreshMeaning}
          disabled={meaningLoading}
          style={{
            padding: '10px 20px',
            background: meaningLoading ? '#9ca3af' : '#059669',
            color: '#fff',
            border: 'none',
            borderRadius: 8,
            fontWeight: 600,
            cursor: meaningLoading ? 'not-allowed' : 'pointer'
          }}
        >
          {meaningLoading ? 'Fetching...' : 'Get Business Description (SEC 10-K)'}
        </button>
      </div>

      {/* Four Ms Cards */}
      {data && (
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', 
          gap: 16,
          marginBottom: 20
        }}>
          {/* Moat Card - Enhanced with Phase C/E */}
          <MCard 
            title="Moat" 
            icon="🏰"
            description="A moat is a durable competitive advantage that protects a company from competitors. Look for high and stable ROIC over many years."
            score={data.moat?.score}
          >
            {/* E2: ROIC Persistence Badge */}
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 4 }}>ROIC Persistence</div>
              <PersistenceBadge score={data.moat?.roic_persistence_score} />
            </div>
            
            <MetricRow 
              label="Avg ROIC" 
              value={formatPct(data.moat?.roic_avg)}
              hint="Return on Invested Capital - measures how efficiently the company uses its capital to generate profits"
              target="≥15%"
            />
            <MetricRow 
              label="Margin Stability" 
              value={formatPct(data.moat?.margin_stability)}
              hint="How consistent are the company's profit margins over time? Higher is better."
              target="≥80%"
            />
            
            {/* Phase C: Gross Margin & Pricing Power */}
            <MetricRow 
              label="Gross Margin" 
              value={formatPct(data.moat?.latest_gross_margin)}
              hint="Revenue minus cost of goods sold, divided by revenue. Higher margins indicate pricing power."
              target="≥30%"
            />
            <MetricRow 
              label="Gross Margin Trend" 
              value={data.moat?.gross_margin_trend !== null && data.moat?.gross_margin_trend !== undefined 
                ? `${data.moat.gross_margin_trend >= 0 ? '+' : ''}${(data.moat.gross_margin_trend * 100).toFixed(2)}%` 
                : 'N/A'}
              hint="Change in gross margin over time. Positive = improving pricing power."
            />
            <MetricRow 
              label="Pricing Power" 
              value={formatPct(data.moat?.pricing_power_score)}
              hint="Composite score based on gross margin level, stability, and trend. Higher = stronger pricing power."
              target="≥60%"
            />
            
            <ScoreBar score={data.moat?.score} label="Overall Moat Strength" />
            <p style={{ fontSize: 12, color: '#6b7280', marginTop: 12, marginBottom: 0 }}>
              <strong>What to look for:</strong> Companies with wide moats have ROIC consistently above 15% for 10+ years.
            </p>
          </MCard>

          {/* Management Card */}
          <MCard 
            title="Management" 
            icon="👔"
            description="Great management allocates capital wisely, reinvesting in the business at high returns or returning cash to shareholders."
            score={data.management?.score}
          >
            <MetricRow 
              label="Reinvestment Ratio" 
              value={formatPct(data.management?.reinvest_ratio_avg)}
              hint="How much of earnings are reinvested back into the business for growth"
            />
            <MetricRow 
              label="Payout Ratio" 
              value={formatPct(data.management?.payout_ratio_avg)}
              hint="How much of earnings are paid out as dividends to shareholders"
            />
            <ScoreBar score={data.management?.score} label="Management Quality" />
            <p style={{ fontSize: 12, color: '#6b7280', marginTop: 12, marginBottom: 0 }}>
              <strong>What to look for:</strong> Owner-oriented managers who think long-term and allocate capital at high returns.
            </p>
          </MCard>

          {/* E3: Balance Sheet Resilience Card - Phase C */}
          {data.balance_sheet_resilience && (
            <MCard 
              title="Balance Sheet" 
              icon="🏦"
              description="Financial strength and ability to weather economic downturns. Strong balance sheets provide safety and flexibility."
            >
              {/* Balance Sheet Score Badge */}
              <div style={{ marginBottom: 12 }}>
                <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 4 }}>Resilience Score</div>
                <PersistenceBadge score={data.balance_sheet_resilience?.score} />
              </div>
              
              <MetricRow 
                label="Interest Coverage" 
                value={data.balance_sheet_resilience?.latest_coverage !== null && data.balance_sheet_resilience?.latest_coverage !== undefined
                  ? `${data.balance_sheet_resilience.latest_coverage.toFixed(1)}x`
                  : 'N/A'}
                hint="EBIT divided by interest expense. Higher = more ability to pay debt obligations."
                target="≥5x"
              />
              <MetricRow 
                label="Debt/Equity" 
                value={data.balance_sheet_resilience?.debt_to_equity !== null && data.balance_sheet_resilience?.debt_to_equity !== undefined
                  ? data.balance_sheet_resilience.debt_to_equity.toFixed(2)
                  : 'N/A'}
                hint="Total debt divided by shareholder equity. Lower = less leveraged."
                target="≤0.5"
              />
              <MetricRow 
                label="Net Debt" 
                value={data.balance_sheet_resilience?.latest_net_debt !== null && data.balance_sheet_resilience?.latest_net_debt !== undefined
                  ? `$${(data.balance_sheet_resilience.latest_net_debt / 1e9).toFixed(1)}B`
                  : 'N/A'}
                hint="Total debt minus cash. Negative = net cash position (good)."
              />
              <MetricRow 
                label="Net Debt Trend" 
                value={data.balance_sheet_resilience?.net_debt_trend !== null && data.balance_sheet_resilience?.net_debt_trend !== undefined
                  ? `${data.balance_sheet_resilience.net_debt_trend >= 0 ? '+' : ''}${(data.balance_sheet_resilience.net_debt_trend * 100).toFixed(1)}%`
                  : 'N/A'}
                hint="Change in net debt over time. Negative = paying down debt (good)."
              />
              
              <p style={{ fontSize: 12, color: '#6b7280', marginTop: 12, marginBottom: 0 }}>
                <strong>What to look for:</strong> Companies with low debt, high coverage ratios, and decreasing debt over time.
              </p>
            </MCard>
          )}

          {/* Margin of Safety Card */}
          <MCard 
            title="Margin of Safety" 
            icon="🛡️"
            description="The discount you should demand below the company's true value to protect against errors in your analysis."
          >
            <div style={{ 
              textAlign: 'center', 
              padding: '20px 0',
              background: '#f9fafb',
              borderRadius: 8,
              marginBottom: 12
            }}>
              <div style={{ fontSize: 48, fontWeight: 700, color: mosInfo.color }}>
                {mosPercent !== undefined ? `${Math.round(mosPercent * 100)}%` : 'N/A'}
              </div>
              <div style={{ fontSize: 14, color: mosInfo.color, fontWeight: 500 }}>
                Recommended Discount
              </div>
            </div>
            <div style={{ 
              padding: '8px 12px', 
              background: '#f3f4f6', 
              borderRadius: 6,
              fontSize: 13,
              color: '#374151'
            }}>
              <strong style={{ color: mosInfo.color }}>{mosInfo.label}</strong>
            </div>
            <p style={{ fontSize: 12, color: '#6b7280', marginTop: 12, marginBottom: 0 }}>
              <strong>Rule of thumb:</strong> Always buy at least 50% below sticker price. Higher MOS = more uncertainty.
            </p>
          </MCard>
        </div>
      )}

      {/* Meaning Section */}
      {meaning && (
        <MCard 
          title="Meaning" 
          icon="💡"
          description="Do you understand this business? Can you explain what they do in simple terms? This is your 'circle of competence'."
        >
          <div style={{ marginBottom: 12 }}>
            <span style={{ 
              display: 'inline-block',
              padding: '4px 10px', 
              borderRadius: 12, 
              background: '#dbeafe',
              color: '#1d4ed8',
              fontSize: 13,
              fontWeight: 500
            }}>
              From SEC 10-K Filing — Item 1. Business
            </span>
          </div>
          <div style={{ 
            background: '#f9fafb', 
            padding: 16, 
            borderRadius: 8,
            maxHeight: 300, 
            overflow: 'auto',
            fontSize: 14,
            lineHeight: 1.6,
            color: '#374151',
            whiteSpace: 'pre-wrap'
          }}>
            {meaning}
          </div>
          <p style={{ fontSize: 12, color: '#6b7280', marginTop: 12, marginBottom: 0 }}>
            <strong>Ask yourself:</strong> Can I explain this business to a 10-year-old? Would I be comfortable owning 100% of this company?
          </p>
        </MCard>
      )}

      {/* Educational Footer */}
      {!data && !meaning && (
        <div style={{ 
          background: '#f0f9ff', 
          border: '1px solid #bae6fd',
          borderRadius: 12, 
          padding: 20 
        }}>
          <h4 style={{ margin: '0 0 12px', color: '#0369a1' }}>What are the Four Ms?</h4>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}>
            <div>
              <strong>🏰 Moat</strong>
              <p style={{ margin: '4px 0 0', fontSize: 13, color: '#0c4a6e' }}>
                A durable competitive advantage that keeps competitors at bay
              </p>
            </div>
            <div>
              <strong>👔 Management</strong>
              <p style={{ margin: '4px 0 0', fontSize: 13, color: '#0c4a6e' }}>
                Honest, capable leaders who allocate capital wisely
              </p>
            </div>
            <div>
              <strong>💡 Meaning</strong>
              <p style={{ margin: '4px 0 0', fontSize: 13, color: '#0c4a6e' }}>
                A business you understand within your circle of competence
              </p>
            </div>
            <div>
              <strong>🛡️ Margin of Safety</strong>
              <p style={{ margin: '4px 0 0', fontSize: 13, color: '#0c4a6e' }}>
                Buying at a big discount to protect against mistakes
              </p>
            </div>
          </div>
          <p style={{ margin: '16px 0 0', fontSize: 13, color: '#0369a1' }}>
            Click the buttons above to analyze {ticker}&apos;s Four Ms!
          </p>
        </div>
      )}
    </section>
  );
}