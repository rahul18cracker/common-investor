'use client';
import { useEffect, useState } from 'react';
import CompanyDashboard from '../../../components/CompanyDashboard';
import ValuationPanel from '../../../components/ValuationPanel';
import FourMsPanel from '../../../components/FourMsPanel';
import AlertsPanel from '../../../components/AlertsPanel';

export default function Company({ params }: { params: { ticker: string } }) {
  const [summary, setSummary] = useState<any>(null);
  const [metrics, setMetrics] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string|undefined>();
  const api = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';

  async function loadAll() {
    setLoading(true);
    try {
      const s = await fetch(`${api}/api/v1/company/${params.ticker}`);
      setSummary(s.status === 404 ? null : await s.json());
      const m = await fetch(`${api}/api/v1/company/${params.ticker}/metrics`);
      setMetrics(await m.json());
      setErr(undefined);
    } catch (e: any) {
      setErr(String(e));
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => { loadAll(); }, [params.ticker]);

  const metricsCSV = `${api}/api/v1/company/${params.ticker}/export/metrics.csv`;

  return (
    <main style={{ padding: 24, maxWidth: 1100, margin: '0 auto' }}>
      <h1>Common Investor — {params.ticker}</h1>
      {loading && <p>Loading...</p>}
      {err && <p style={{ color: 'red' }}>{err}</p>}
      <section style={{ marginTop: 16 }}>
        <h2>Data</h2>
        {!summary && <p>No data. Click ingest.</p>}
        {summary && <pre style={{ background: '#f6f6f6', padding: 12 }}>{JSON.stringify(summary, null, 2)}</pre>}
        <button onClick={async () => { await fetch(`${api}/api/v1/company/${params.ticker}/ingest`, { method: 'POST' }); alert('Ingest queued. Reload after a bit.'); }}>Ingest</button>
        <button onClick={() => loadAll()} style={{ marginLeft: 8 }}>Reload</button>
        {' '}<a href={metricsCSV} target="_blank" rel="noreferrer">Export Metrics CSV</a>
      </section>

      <CompanyDashboard api={api} ticker={params.ticker} />
      <ValuationPanel api={api} ticker={params.ticker} />
      <FourMsPanel api={api} ticker={params.ticker} />
      <AlertsPanel api={api} ticker={params.ticker} />
    </main>
  );
}