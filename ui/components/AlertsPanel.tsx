'use client';
import { useEffect, useState } from 'react';

interface Alert {
  id: number;
  rule_type: string;
  threshold: number | null;
  enabled: boolean;
}

export default function AlertsPanel({ api, ticker }:{ api:string, ticker:string }){
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const reload = async (): Promise<void> => {
    try {
      const res = await fetch(`${api}/api/v1/company/${ticker}/alerts`);
      setAlerts(res.status===200 ? await res.json() : []);
    } catch (e: unknown) {
      console.error('Failed to load alerts:', e instanceof Error ? e.message : String(e));
    }
  };
  useEffect(()=>{ reload(); }, [api, ticker]);

  const createPriceBelowMOS = async (): Promise<void> => {
    try {
      await fetch(`${api}/api/v1/company/${ticker}/alerts`,{ method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ rule_type:'price_below_mos' }) });
      await reload();
    } catch (e: unknown) {
      console.error('Failed to create alert:', e instanceof Error ? e.message : String(e));
    }
  };
  const createBelowThreshold = async (): Promise<void> => {
    const thr = prompt('Threshold price?');
    if (!thr) return;
    try {
      await fetch(`${api}/api/v1/company/${ticker}/alerts`,{ method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ rule_type:'price_below_threshold', threshold: Number(thr) }) });
      await reload();
    } catch (e: unknown) {
      console.error('Failed to create alert:', e instanceof Error ? e.message : String(e));
    }
  };
  const toggleAlert = async (id:number, enabled:boolean): Promise<void> => {
    try {
      await fetch(`${api}/api/v1/alerts/${id}`, { method:'PATCH', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ enabled }) });
      await reload();
    } catch (e: unknown) {
      console.error('Failed to toggle alert:', e instanceof Error ? e.message : String(e));
    }
  };
  const deleteAlert = async (id:number): Promise<void> => {
    try {
      await fetch(`${api}/api/v1/alerts/${id}`, { method:'DELETE' });
      await reload();
    } catch (e: unknown) {
      console.error('Failed to delete alert:', e instanceof Error ? e.message : String(e));
    }
  };
  return (
    <section style={{ marginTop: 24 }}>
      <h2>Alerts</h2>
      <div style={{ display:'flex', gap:12 }}>
        <button onClick={createPriceBelowMOS}>Add: Price &lt; MOS</button>
        <button onClick={createBelowThreshold}>Add: Price &lt; Threshold</button>
      </div>
      <table style={{ width:'100%', marginTop: 12, borderCollapse:'collapse' }}>
        <thead>
          <tr>
            <th style={{ textAlign:'left', borderBottom:'1px solid #ddd', padding:6 }}>ID</th>
            <th style={{ textAlign:'left', borderBottom:'1px solid #ddd', padding:6 }}>Rule</th>
            <th style={{ textAlign:'left', borderBottom:'1px solid #ddd', padding:6 }}>Threshold</th>
            <th style={{ textAlign:'left', borderBottom:'1px solid #ddd', padding:6 }}>Enabled</th>
            <th style={{ textAlign:'left', borderBottom:'1px solid #ddd', padding:6 }}>Actions</th>
          </tr>
        </thead>
        <tbody>
          {alerts.map((a: Alert)=> (
            <tr key={a.id}>
              <td style={{ padding:6 }}>{a.id}</td>
              <td style={{ padding:6 }}>{a.rule_type}</td>
              <td style={{ padding:6 }}>{a.threshold ?? '—'}</td>
              <td style={{ padding:6 }}>{String(a.enabled)}</td>
              <td style={{ padding:6 }}>
                <button onClick={()=>toggleAlert(a.id, !a.enabled)}>{a.enabled ? 'Disable':'Enable'}</button>
                <button onClick={()=>deleteAlert(a.id)} style={{ marginLeft: 8 }}>Delete</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}