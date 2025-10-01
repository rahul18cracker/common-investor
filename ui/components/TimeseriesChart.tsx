'use client';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend, CartesianGrid } from 'recharts';

export default function TimeseriesChart({ data, lines }:{ data:any[], lines:{dataKey:string, name:string, yAxisId?:string}[] }){
  return (
    <div style={{ width: '100%', height: 300 }}>
      <ResponsiveContainer>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="fy"/>
          <YAxis yAxisId="left"/>
          <YAxis yAxisId="right" orientation="right"/>
          <Tooltip/>
          <Legend/>
          {lines.map((l,idx)=>(
            <Line key={idx} type="monotone" dataKey={l.dataKey} name={l.name} yAxisId={l.yAxisId || 'left'} dot={false}/>
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}