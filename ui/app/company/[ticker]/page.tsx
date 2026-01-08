'use client';
import { useEffect, useState } from 'react';
import BigFivePanel from '../../../components/BigFivePanel';
import IncomeStatementPanel from '../../../components/IncomeStatementPanel';
import CompanyDashboard from '../../../components/CompanyDashboard';
import ValuationPanel from '../../../components/ValuationPanel';
import FourMsPanel from '../../../components/FourMsPanel';
import AlertsPanel from '../../../components/AlertsPanel';

export default function Company({ params }: { params: { ticker: string } }) {
  const [summary, setSummary] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | undefined>();
  const [ingesting, setIngesting] = useState(false);
  const api = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';

  async function loadAll() {
    setLoading(true);
    try {
      const s = await fetch(`${api}/api/v1/company/${params.ticker}`);
      setSummary(s.status === 404 ? null : await s.json());
      setErr(undefined);
    } catch (e: any) {
      setErr(String(e));
    } finally {
      setLoading(false);
    }
  }

  async function handleIngest() {
    setIngesting(true);
    try {
      await fetch(`${api}/api/v1/company/${params.ticker}/ingest`, { method: 'POST' });
      alert('Ingest queued. Data will be available in 30-60 seconds. Click Reload to refresh.');
    } finally {
      setIngesting(false);
    }
  }

  useEffect(() => { loadAll(); }, [params.ticker]);

  const metricsCSV = `${api}/api/v1/company/${params.ticker}/export/metrics.csv`;

  return (
    <main style={{ padding: '24px 24px 48px', maxWidth: 1200, margin: '0 auto' }}>
      {/* Header */}
      <header style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'flex-start',
        flexWrap: 'wrap',
        gap: 16,
        marginBottom: 24,
        paddingBottom: 20,
        borderBottom: '1px solid #e5e7eb'
      }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 32, fontWeight: 700, color: '#111' }}>
            {params.ticker}
          </h1>
          {summary && (
            <p style={{ margin: '4px 0 0', color: '#6b7280', fontSize: 16 }}>
              {summary.name || 'Company Analysis'}
            </p>
          )}
          <p style={{ margin: '8px 0 0', color: '#9ca3af', fontSize: 13 }}>
            Rule #1 Investing Analysis powered by SEC EDGAR data
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <button 
            onClick={handleIngest}
            disabled={ingesting}
            style={{
              padding: '10px 20px',
              background: ingesting ? '#9ca3af' : '#2563eb',
              color: '#fff',
              border: 'none',
              borderRadius: 8,
              fontWeight: 600,
              cursor: ingesting ? 'not-allowed' : 'pointer'
            }}
          >
            {ingesting ? 'Ingesting...' : 'Ingest SEC Data'}
          </button>
          <button 
            onClick={() => loadAll()}
            style={{
              padding: '10px 20px',
              background: '#f3f4f6',
              color: '#374151',
              border: '1px solid #d1d5db',
              borderRadius: 8,
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            Reload
          </button>
          <a 
            href={metricsCSV} 
            target="_blank" 
            rel="noreferrer"
            style={{
              padding: '10px 20px',
              background: '#f3f4f6',
              color: '#374151',
              border: '1px solid #d1d5db',
              borderRadius: 8,
              fontWeight: 600,
              textDecoration: 'none'
            }}
          >
            Export CSV
          </a>
        </div>
      </header>

      {/* Status Messages */}
      {loading && (
        <div style={{ padding: 20, background: '#f0f9ff', borderRadius: 8, marginBottom: 24 }}>
          <p style={{ margin: 0, color: '#0369a1' }}>Loading company data...</p>
        </div>
      )}
      {err && (
        <div style={{ padding: 20, background: '#fef2f2', borderRadius: 8, marginBottom: 24 }}>
          <p style={{ margin: 0, color: '#dc2626' }}>Error: {err}</p>
        </div>
      )}
      {!loading && !summary && (
        <div style={{ padding: 20, background: '#fffbeb', borderRadius: 8, marginBottom: 24 }}>
          <p style={{ margin: 0, color: '#b45309' }}>
            No data available for {params.ticker}. Click &quot;Ingest SEC Data&quot; to fetch financial information from SEC EDGAR.
          </p>
        </div>
      )}

      {/* Company Summary (collapsible) */}
      {summary && (
        <details style={{ marginBottom: 24 }}>
          <summary style={{ 
            cursor: 'pointer', 
            padding: '12px 16px',
            background: '#f9fafb',
            borderRadius: 8,
            fontWeight: 600,
            color: '#374151'
          }}>
            View Raw Company Data
          </summary>
          <pre style={{ 
            background: '#f6f6f6', 
            padding: 16, 
            borderRadius: '0 0 8px 8px',
            overflow: 'auto',
            fontSize: 12
          }}>
            {JSON.stringify(summary, null, 2)}
          </pre>
        </details>
      )}

      {/* Main Analysis Sections */}
      <BigFivePanel api={api} ticker={params.ticker} />
      <IncomeStatementPanel api={api} ticker={params.ticker} />
      <FourMsPanel api={api} ticker={params.ticker} />
      <ValuationPanel api={api} ticker={params.ticker} />
      <CompanyDashboard api={api} ticker={params.ticker} />
      <AlertsPanel api={api} ticker={params.ticker} />
    </main>
  );
}