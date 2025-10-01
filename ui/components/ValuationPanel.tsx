'use client';
import { useState } from 'react';

export default function ValuationPanel({ api, ticker }:{ api:string, ticker:string }){
  const [mosPct, setMosPct] = useState<number>(0.5);
  const [growth, setGrowth] = useState<number | ''>('');
  const [peCap, setPeCap] = useState<number>(20);
  const [discount, setDiscount] = useState<number>(0.15);
  const [valuation, setValuation] = useState<any>(null);

  async function runValuation(){
    const res = await fetch(`${api}/api/v1/company/${ticker}/valuation`, {
      method: 'POST', headers: { 'Content-Type':'application/json' },
      body: JSON.stringify({ mos_pct: mosPct, g: growth===''?null:growth, pe_cap: peCap, discount })
    });
    setValuation(await res.json());
  }

  const exportUrl = `${api}/api/v1/company/${ticker}/export/valuation.json?mos_pct=${mosPct}`;

  return (
    <section style={{ marginTop: 24 }}>
      <h2>Valuation</h2>
      <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr 1fr 1fr', gap:12, maxWidth:700 }}>
        <label>MOS %
          <input type="range" min={0} max={90} value={mosPct*100} onChange={e=>setMosPct(Number(e.target.value)/100)} />
          <span>{Math.round(mosPct*100)}%</span>
        </label>
        <label>Growth g
          <input type="range" min={0} max={30} value={(growth===''?10:Math.round(Number(growth*100)))/1} onChange={e=>setGrowth(Number(e.target.value)/100)} />
          <span>{growth===''?'auto':(Number(growth*100).toFixed(0)+'%')}</span>
        </label>
        <label>PE cap
          <input type="range" min={5} max={40} value={peCap} onChange={e=>setPeCap(Number(e.target.value))} />
          <span>{peCap}</span>
        </label>
        <label>Discount
          <input type="range" min={5} max={25} value={Math.round(discount*100)} onChange={e=>setDiscount(Number(e.target.value)/100)} />
          <span>{Math.round(discount*100)}%</span>
        </label>
      </div>
      <div style={{ marginTop: 8 }}>
        <button onClick={runValuation}>Run Valuation</button>
        {' '}<a href={exportUrl} target="_blank" rel="noreferrer">Export JSON</a>
      </div>
      {valuation && <pre style={{ background:'#f6f6f6', padding:12, marginTop:12 }}>{JSON.stringify(valuation, null, 2)}</pre>}
    </section>
  )
}