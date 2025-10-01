'use client';
import { useEffect, useState } from 'react';

export default function AlertsPanel({ api, ticker }:{ api:string, ticker:string }){
  const [alerts, setAlerts] = useState<any[]>([]);
  async function reload(){
    const res = await fetch(`${api}/api/v1/company/${ticker}/alerts`);
    setAlerts(res.status===200 ? await res.json() : []);
  }
  useEffect(()=>{ reload(); }, [ticker]);

  async function createPriceBelowMOS(){
    await fetch(`${api}/api/v1/company/${ticker}/alerts`,{ method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ rule_type:'price_below_mos' }) });
    reload();
  }
  async function createBelowThreshold(){
    const thr = prompt('Threshold price?');
    if (!thr) return;
    await fetch(`${api}/api/v1/company/${ticker}/alerts`,{ method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ rule_type:'price_below_threshold', threshold: Number(thr) }) });
    reload();
  }
  async function toggleAlert(id:number, enabled:boolean){
    await fetch(`${api}/api/v1/alerts/${id}`, { method:'PATCH', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ enabled }) });
    reload();
  }
  async function deleteAlert(id:number){
    await fetch(`${api}/api/v1/alerts/${id}`, { method:'DELETE' });
    reload();
  }
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
          {alerts.map(a=> (
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