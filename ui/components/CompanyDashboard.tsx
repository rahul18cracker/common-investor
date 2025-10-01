'use client';
import { useEffect, useState } from 'react';
import TimeseriesChart from './TimeseriesChart';

export default function CompanyDashboard({ api, ticker }:{ api:string, ticker:string }){
  const [timeseries, setTimeseries] = useState<any|null>(null);
  const [err, setErr] = useState<string|undefined>();

  useEffect(()=>{
    (async ()=>{
      try{
        const res = await fetch(`${api}/api/v1/company/${ticker}/timeseries`);
        setTimeseries(await res.json());
      }catch(e:any){ setErr(String(e)); }
    })();
  }, [api, ticker]);

  if(err) return <p style={{ color:'red' }}>{err}</p>;
  if(!timeseries) return <p>Loading charts...</p>;

  const isData = timeseries.is || [];
  const roicData = (timeseries.roic || []).map((x:any)=>({ fy:x.fy, roic: x.roic }));
  const covData = (timeseries.coverage || []).map((x:any)=>({ fy:x.fy, coverage: x.coverage }));

  return (
    <section style={{ marginTop: 24 }}>
      <h2>Dashboards</h2>
      <h3>Revenue & EPS</h3>
      <TimeseriesChart data={isData} lines={[{ dataKey:'revenue', name:'Revenue', yAxisId:'left' }, { dataKey:'eps', name:'EPS', yAxisId:'right' }]} />
      <h3>ROIC</h3>
      <TimeseriesChart data={roicData} lines={[{ dataKey:'roic', name:'ROIC', yAxisId:'left' }]} />
      <h3>Interest Coverage</h3>
      <TimeseriesChart data={covData} lines={[{ dataKey:'coverage', name:'Coverage', yAxisId:'left' }]} />
    </section>
  )
}