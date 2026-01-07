'use client';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend, CartesianGrid, ReferenceLine } from 'recharts';

// Default colors for lines
const DEFAULT_COLORS = ['#2563eb', '#16a34a', '#dc2626', '#7c3aed', '#0891b2', '#ea580c'];

interface LineConfig {
  dataKey: string;
  name: string;
  yAxisId?: string;
  color?: string;
}

interface ReferenceLineConfig {
  y: number;
  label: string;
  color: string;
}

interface TimeseriesChartProps {
  data: any[];
  lines: LineConfig[];
  height?: number;
  formatLeftAxis?: (value: number) => string;
  formatRightAxis?: (value: number) => string;
  referenceLine?: ReferenceLineConfig;
}

export default function TimeseriesChart({ 
  data, 
  lines,
  height = 300,
  formatLeftAxis,
  formatRightAxis,
  referenceLine
}: TimeseriesChartProps) {
  // Check if we need a right axis
  const hasRightAxis = lines.some(l => l.yAxisId === 'right');

  return (
    <div style={{ width: '100%', height }}>
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis 
            dataKey="fy" 
            tick={{ fontSize: 12, fill: '#6b7280' }}
            axisLine={{ stroke: '#d1d5db' }}
            tickLine={{ stroke: '#d1d5db' }}
          />
          <YAxis 
            yAxisId="left"
            tick={{ fontSize: 12, fill: '#6b7280' }}
            axisLine={{ stroke: '#d1d5db' }}
            tickLine={{ stroke: '#d1d5db' }}
            tickFormatter={formatLeftAxis}
            width={60}
          />
          {hasRightAxis && (
            <YAxis 
              yAxisId="right" 
              orientation="right"
              tick={{ fontSize: 12, fill: '#6b7280' }}
              axisLine={{ stroke: '#d1d5db' }}
              tickLine={{ stroke: '#d1d5db' }}
              tickFormatter={formatRightAxis}
              width={60}
            />
          )}
          <Tooltip 
            contentStyle={{ 
              background: '#fff', 
              border: '1px solid #e5e7eb',
              borderRadius: 8,
              boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)'
            }}
            labelStyle={{ fontWeight: 600, marginBottom: 4 }}
            formatter={(value: number, name: string) => {
              // Find the line config for this data key
              const lineConfig = lines.find(l => l.name === name);
              if (lineConfig?.yAxisId === 'right' && formatRightAxis) {
                return [formatRightAxis(value), name];
              }
              if (formatLeftAxis) {
                return [formatLeftAxis(value), name];
              }
              return [value.toLocaleString(), name];
            }}
          />
          <Legend 
            wrapperStyle={{ paddingTop: 10 }}
            iconType="line"
          />
          {referenceLine && (
            <ReferenceLine 
              y={referenceLine.y} 
              yAxisId="left"
              stroke={referenceLine.color} 
              strokeDasharray="5 5"
              label={{ 
                value: referenceLine.label, 
                position: 'right',
                fill: referenceLine.color,
                fontSize: 11
              }}
            />
          )}
          {lines.map((l, idx) => (
            <Line 
              key={idx} 
              type="monotone" 
              dataKey={l.dataKey} 
              name={l.name} 
              yAxisId={l.yAxisId || 'left'} 
              stroke={l.color || DEFAULT_COLORS[idx % DEFAULT_COLORS.length]}
              strokeWidth={2}
              dot={{ r: 3, fill: l.color || DEFAULT_COLORS[idx % DEFAULT_COLORS.length] }}
              activeDot={{ r: 5, strokeWidth: 2 }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}