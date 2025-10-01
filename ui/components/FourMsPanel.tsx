'use client';
import { useState } from 'react';

export default function FourMsPanel({ api, ticker }:{ api:string, ticker:string }){
  const [data, setData] = useState<any>(null);
  const [meaning, setMeaning] = useState<string>('');

  async function loadSummary(){
    const res = await fetch(`${api}/api/v1/company/${ticker}/fourm`);
    setData(await res.json());
  }
  async function refreshMeaning(){
    const res = await fetch(`${api}/api/v1/company/${ticker}/fourm/meaning/refresh`, { method:'POST' });
    const j = await res.json();
    setMeaning(j.item1_excerpt || '');
  }

  return (
    <section style={{ marginTop: 24 }}>
      <h2>Four Ms</h2>
      <div style={{ display:'flex', gap:12 }}>
        <button onClick={loadSummary}>Compute Moat/Management/MOS</button>
        <button onClick={refreshMeaning}>Fetch Meaning (Item 1)</button>
      </div>
      {data && (
        <div style={{ marginTop: 12, display:'grid', gridTemplateColumns:'1fr 1fr 1fr', gap:12 }}>
          <div style={{ border:'1px solid #ddd', borderRadius:8, padding:12 }}>
            <h3>Moat</h3>
            <p>ROIC avg: {data.moat?.roic_avg?.toFixed?.(3) ?? 'n/a'}</p>
            <p>Margin stability: {data.moat?.margin_stability?.toFixed?.(3) ?? 'n/a'}</p>
            <p><b>Score:</b> {data.moat?.score?.toFixed?.(3) ?? 'n/a'}</p>
          </div>
          <div style={{ border:'1px solid #ddd', borderRadius:8, padding:12 }}>
            <h3>Management</h3>
            <p>Reinvest ratio avg: {data.management?.reinvest_ratio_avg?.toFixed?.(3) ?? 'n/a'}</p>
            <p>Payout ratio avg: {data.management?.payout_ratio_avg?.toFixed?.(3) ?? 'n/a'}</p>
            <p><b>Score:</b> {data.management?.score?.toFixed?.(3) ?? 'n/a'}</p>
          </div>
          <div style={{ border:'1px solid #ddd', borderRadius:8, padding:12 }}>
            <h3>Margin of Safety (Recommendation)</h3>
            <p><b>Recommended MOS:</b> {Math.round((data.mos_recommendation?.recommended_mos ?? 0)*100)}%</p>
          </div>
        </div>
      )}
      {meaning && (
        <div style={{ marginTop: 12 }}>
          <h3>Meaning — Item 1. Business (excerpt)</h3>
          <pre style={{ background:'#f6f6f6', padding:12, maxHeight:300, overflow:'auto' }}>{meaning}</pre>
        </div>
      )}
    </section>
  )
}