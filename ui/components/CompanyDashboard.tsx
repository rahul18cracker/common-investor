'use client';
import { useEffect, useState } from 'react';
import TimeseriesChart from './TimeseriesChart';

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

// Chart card wrapper
function ChartCard({
  title,
  icon,
  description,
  children,
  insight
}: {
  title: string;
  icon: string;
  description: string;
  children: React.ReactNode;
  insight?: string;
}) {
  return (
    <div style={{
      border: '1px solid #e5e7eb',
      borderRadius: 12,
      padding: 20,
      background: '#fff',
      boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
        <span style={{ fontSize: 24 }}>{icon}</span>
        <h3 style={{ margin: 0, fontSize: 18, fontWeight: 600, color: '#111' }}>{title}</h3>
        <InfoTip text={description} />
      </div>
      {children}
      {insight && (
        <div style={{
          marginTop: 12,
          padding: '10px 12px',
          background: '#f0f9ff',
          borderRadius: 6,
          fontSize: 13,
          color: '#0369a1'
        }}>
          <strong>What to look for:</strong> {insight}
        </div>
      )}
    </div>
  );
}

export default function CompanyDashboard({ api, ticker }: { api: string; ticker: string }) {
  const [timeseries, setTimeseries] = useState<any | null>(null);
  const [err, setErr] = useState<string | undefined>();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const res = await fetch(`${api}/api/v1/company/${ticker}/timeseries`);
        setTimeseries(await res.json());
        setErr(undefined);
      } catch (e: any) {
        setErr(String(e));
      } finally {
        setLoading(false);
      }
    })();
  }, [api, ticker]);

  const isData = timeseries?.is || [];
  const roicData = (timeseries?.roic || []).map((x: any) => ({ 
    fy: x.fy, 
    roic: x.roic,
    roicPct: x.roic ? (x.roic * 100).toFixed(1) : null
  }));
  const covData = (timeseries?.coverage || []).map((x: any) => ({ 
    fy: x.fy, 
    coverage: x.coverage 
  }));

  // Calculate some insights
  const latestROIC = roicData.length > 0 ? roicData[roicData.length - 1]?.roic : null;
  const avgROIC = roicData.length > 0 
    ? roicData.reduce((sum: number, x: any) => sum + (x.roic || 0), 0) / roicData.length 
    : null;
  const roicTrend = roicData.length >= 2 
    ? (roicData[roicData.length - 1]?.roic || 0) > (roicData[0]?.roic || 0) ? 'improving' : 'declining'
    : 'unknown';

  return (
    <section style={{ marginTop: 32 }}>
      {/* Header */}
      <div style={{ marginBottom: 20 }}>
        <h2 style={{ margin: 0, fontSize: 24, fontWeight: 700, color: '#111' }}>
          Historical Trends
        </h2>
        <p style={{ margin: '8px 0 0', color: '#6b7280', fontSize: 14 }}>
          Track key financial metrics over time to identify consistent growth patterns
        </p>
      </div>

      {/* Loading/Error States */}
      {loading && (
        <div style={{ padding: 40, textAlign: 'center', color: '#6b7280' }}>
          Loading historical data...
        </div>
      )}
      {err && (
        <div style={{ padding: 20, background: '#fef2f2', borderRadius: 8, color: '#dc2626' }}>
          Error loading charts: {err}
        </div>
      )}

      {/* Charts Grid */}
      {!loading && !err && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))',
          gap: 20
        }}>
          {/* Revenue & EPS Chart */}
          <ChartCard
            title="Revenue & EPS"
            icon="📈"
            description="Revenue is the company's total sales. EPS (Earnings Per Share) is the profit allocated to each share of stock."
            insight="Look for consistent upward trends in both metrics. Revenue should grow steadily, and EPS should follow."
          >
            {isData.length > 0 ? (
              <TimeseriesChart 
                data={isData} 
                lines={[
                  { dataKey: 'revenue', name: 'Revenue', yAxisId: 'left', color: '#2563eb' },
                  { dataKey: 'eps', name: 'EPS', yAxisId: 'right', color: '#16a34a' }
                ]}
                height={250}
                formatLeftAxis={(v) => `$${(v / 1e9).toFixed(0)}B`}
                formatRightAxis={(v) => `$${v.toFixed(2)}`}
              />
            ) : (
              <div style={{ padding: 40, textAlign: 'center', color: '#9ca3af' }}>
                No revenue/EPS data available
              </div>
            )}
          </ChartCard>

          {/* ROIC Chart */}
          <ChartCard
            title="Return on Invested Capital (ROIC)"
            icon="📊"
            description="ROIC measures how efficiently the company uses its capital to generate profits. It's a key indicator of competitive advantage."
            insight={`Target: ≥15% consistently. ${avgROIC !== null ? `Average ROIC: ${(avgROIC * 100).toFixed(1)}%. Trend: ${roicTrend}.` : ''}`}
          >
            {roicData.length > 0 ? (
              <>
                <TimeseriesChart 
                  data={roicData} 
                  lines={[
                    { dataKey: 'roic', name: 'ROIC', yAxisId: 'left', color: '#7c3aed' }
                  ]}
                  height={250}
                  formatLeftAxis={(v) => `${(v * 100).toFixed(0)}%`}
                  referenceLine={{ y: 0.15, label: '15% Target', color: '#dc2626' }}
                />
                {latestROIC !== null && (
                  <div style={{
                    display: 'flex',
                    justifyContent: 'space-around',
                    marginTop: 12,
                    padding: '8px 0',
                    borderTop: '1px solid #f3f4f6'
                  }}>
                    <div style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: 12, color: '#6b7280' }}>Latest ROIC</div>
                      <div style={{ 
                        fontSize: 18, 
                        fontWeight: 700, 
                        color: latestROIC >= 0.15 ? '#16a34a' : '#dc2626' 
                      }}>
                        {(latestROIC * 100).toFixed(1)}%
                      </div>
                    </div>
                    <div style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: 12, color: '#6b7280' }}>Average ROIC</div>
                      <div style={{ 
                        fontSize: 18, 
                        fontWeight: 700, 
                        color: avgROIC !== null && avgROIC >= 0.15 ? '#16a34a' : '#dc2626' 
                      }}>
                        {avgROIC !== null ? `${(avgROIC * 100).toFixed(1)}%` : 'N/A'}
                      </div>
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div style={{ padding: 40, textAlign: 'center', color: '#9ca3af' }}>
                No ROIC data available
              </div>
            )}
          </ChartCard>

          {/* Interest Coverage Chart */}
          <ChartCard
            title="Interest Coverage Ratio"
            icon="🏦"
            description="Interest Coverage shows how easily the company can pay interest on its debt. Higher is better and indicates financial strength."
            insight="Target: ≥5x coverage. Below 2x is a warning sign of potential debt problems."
          >
            {covData.length > 0 ? (
              <TimeseriesChart 
                data={covData} 
                lines={[
                  { dataKey: 'coverage', name: 'Interest Coverage', yAxisId: 'left', color: '#0891b2' }
                ]}
                height={250}
                formatLeftAxis={(v) => `${v.toFixed(1)}x`}
                referenceLine={{ y: 5, label: '5x Target', color: '#16a34a' }}
              />
            ) : (
              <div style={{ padding: 40, textAlign: 'center', color: '#9ca3af' }}>
                No interest coverage data available
              </div>
            )}
          </ChartCard>
        </div>
      )}

      {/* Educational Footer */}
      {!loading && !err && isData.length === 0 && roicData.length === 0 && (
        <div style={{
          padding: 20,
          background: '#fffbeb',
          border: '1px solid #fcd34d',
          borderRadius: 12,
          marginTop: 20
        }}>
          <h4 style={{ margin: '0 0 8px', color: '#b45309' }}>No Historical Data Available</h4>
          <p style={{ margin: 0, fontSize: 14, color: '#92400e' }}>
            Historical trend data hasn&apos;t been loaded yet. Click &quot;Ingest SEC Data&quot; at the top of the page to fetch financial data from SEC EDGAR filings.
          </p>
        </div>
      )}
    </section>
  );
}