'use client';
import { useState } from 'react';

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

// Slider input component
function SliderInput({
  label,
  hint,
  value,
  displayValue,
  min,
  max,
  step = 1,
  onChange
}: {
  label: string;
  hint: string;
  value: number;
  displayValue: string;
  min: number;
  max: number;
  step?: number;
  onChange: (v: number) => void;
}) {
  return (
    <div style={{ 
      padding: 16, 
      background: '#f9fafb', 
      borderRadius: 8,
      border: '1px solid #e5e7eb'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: 8 }}>
        <span style={{ fontSize: 14, fontWeight: 600, color: '#374151' }}>{label}</span>
        <InfoTip text={hint} />
      </div>
      <input 
        type="range" 
        min={min} 
        max={max} 
        step={step}
        value={value} 
        onChange={e => onChange(Number(e.target.value))}
        style={{ width: '100%', cursor: 'pointer' }}
      />
      <div style={{ 
        textAlign: 'center', 
        fontSize: 20, 
        fontWeight: 700, 
        color: '#2563eb',
        marginTop: 8
      }}>
        {displayValue}
      </div>
    </div>
  );
}

// Price display card
function PriceCard({
  label,
  value,
  description,
  highlight = false,
  icon
}: {
  label: string;
  value: number | null | undefined;
  description: string;
  highlight?: boolean;
  icon: string;
}) {
  const formatted = value !== null && value !== undefined 
    ? `$${value.toFixed(2)}` 
    : 'N/A';
  
  return (
    <div style={{
      padding: 20,
      background: highlight ? '#eff6ff' : '#fff',
      border: highlight ? '2px solid #2563eb' : '1px solid #e5e7eb',
      borderRadius: 12,
      textAlign: 'center'
    }}>
      <div style={{ fontSize: 28, marginBottom: 8 }}>{icon}</div>
      <div style={{ fontSize: 13, color: '#6b7280', marginBottom: 4 }}>{label}</div>
      <div style={{ 
        fontSize: 32, 
        fontWeight: 700, 
        color: highlight ? '#2563eb' : '#111',
        marginBottom: 8
      }}>
        {formatted}
      </div>
      <div style={{ fontSize: 12, color: '#9ca3af' }}>{description}</div>
    </div>
  );
}

// Metric row for additional details
function MetricRow({ label, value }: { label: string; value: string }) {
  return (
    <div style={{
      display: 'flex',
      justifyContent: 'space-between',
      padding: '8px 0',
      borderBottom: '1px solid #f3f4f6'
    }}>
      <span style={{ fontSize: 14, color: '#6b7280' }}>{label}</span>
      <span style={{ fontSize: 14, fontWeight: 600, color: '#111' }}>{value}</span>
    </div>
  );
}

export default function ValuationPanel({ api, ticker }: { api: string; ticker: string }) {
  const [mosPct, setMosPct] = useState<number>(50);
  const [growth, setGrowth] = useState<number>(10);
  const [peCap, setPeCap] = useState<number>(20);
  const [discount, setDiscount] = useState<number>(15);
  const [valuation, setValuation] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);

  async function runValuation() {
    setLoading(true);
    try {
      const res = await fetch(`${api}/api/v1/company/${ticker}/valuation`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mos_pct: mosPct / 100,
          g: growth / 100,
          pe_cap: peCap,
          discount: discount / 100
        })
      });
      setValuation(await res.json());
    } finally {
      setLoading(false);
    }
  }

  const exportUrl = `${api}/api/v1/company/${ticker}/export/valuation.json?mos_pct=${mosPct / 100}`;

  return (
    <section style={{ marginTop: 32 }}>
      {/* Header */}
      <div style={{ marginBottom: 20 }}>
        <h2 style={{ margin: 0, fontSize: 24, fontWeight: 700, color: '#111' }}>
          Valuation Calculator
        </h2>
        <p style={{ margin: '8px 0 0', color: '#6b7280', fontSize: 14 }}>
          Calculate the intrinsic value using Rule #1 valuation methods
        </p>
      </div>

      {/* Input Controls */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: 16,
        marginBottom: 20
      }}>
        <SliderInput
          label="Margin of Safety"
          hint="The discount you require below the sticker price. Rule #1 recommends 50% to protect against errors in your analysis."
          value={mosPct}
          displayValue={`${mosPct}%`}
          min={0}
          max={80}
          step={5}
          onChange={setMosPct}
        />
        <SliderInput
          label="Growth Rate (g)"
          hint="Expected annual EPS growth rate for the next 10 years. Use historical growth or analyst estimates. Be conservative!"
          value={growth}
          displayValue={`${growth}%`}
          min={0}
          max={30}
          onChange={setGrowth}
        />
      </div>

      {/* Advanced Settings Toggle */}
      <button
        onClick={() => setShowAdvanced(!showAdvanced)}
        style={{
          background: 'none',
          border: 'none',
          color: '#2563eb',
          fontSize: 14,
          cursor: 'pointer',
          marginBottom: 16,
          display: 'flex',
          alignItems: 'center',
          gap: 4
        }}
      >
        {showAdvanced ? '▼' : '▶'} Advanced Settings
      </button>

      {showAdvanced && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: 16,
          marginBottom: 20,
          padding: 16,
          background: '#f9fafb',
          borderRadius: 8
        }}>
          <SliderInput
            label="PE Cap"
            hint="Maximum PE ratio to use in valuation. Rule #1 uses 2x growth rate, capped at this value. Conservative investors use lower caps."
            value={peCap}
            displayValue={`${peCap}x`}
            min={5}
            max={40}
            onChange={setPeCap}
          />
          <SliderInput
            label="Discount Rate"
            hint="Your required annual return (minimum acceptable rate of return). Rule #1 uses 15% as the standard."
            value={discount}
            displayValue={`${discount}%`}
            min={8}
            max={25}
            onChange={setDiscount}
          />
        </div>
      )}

      {/* Action Buttons */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 24 }}>
        <button
          onClick={runValuation}
          disabled={loading}
          style={{
            padding: '12px 24px',
            background: loading ? '#9ca3af' : '#2563eb',
            color: '#fff',
            border: 'none',
            borderRadius: 8,
            fontWeight: 600,
            fontSize: 16,
            cursor: loading ? 'not-allowed' : 'pointer'
          }}
        >
          {loading ? 'Calculating...' : 'Calculate Valuation'}
        </button>
        <a
          href={exportUrl}
          target="_blank"
          rel="noreferrer"
          style={{
            padding: '12px 24px',
            background: '#f3f4f6',
            color: '#374151',
            border: '1px solid #d1d5db',
            borderRadius: 8,
            fontWeight: 600,
            textDecoration: 'none',
            display: 'flex',
            alignItems: 'center'
          }}
        >
          Export JSON
        </a>
      </div>

      {/* Results */}
      {valuation && (
        <div>
          {/* Price Cards */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
            gap: 16,
            marginBottom: 24
          }}>
            <PriceCard
              label="Sticker Price"
              value={valuation.sticker}
              description="Fair value based on future earnings"
              icon="🏷️"
            />
            <PriceCard
              label="MOS Price"
              value={valuation.mos_price}
              description={`Buy below this (${mosPct}% discount)`}
              highlight={true}
              icon="🎯"
            />
            <PriceCard
              label="Ten Cap Price"
              value={valuation.ten_cap_price}
              description="Based on 10% owner earnings yield"
              icon="💰"
            />
            <PriceCard
              label="Payback Time"
              value={valuation.payback_years}
              description="Years to recoup investment"
              icon="⏱️"
            />
          </div>

          {/* Calculation Details */}
          <details style={{ marginBottom: 16 }}>
            <summary style={{
              cursor: 'pointer',
              padding: '12px 16px',
              background: '#f9fafb',
              borderRadius: 8,
              fontWeight: 600,
              color: '#374151'
            }}>
              View Calculation Details
            </summary>
            <div style={{
              padding: 16,
              background: '#fff',
              border: '1px solid #e5e7eb',
              borderRadius: '0 0 8px 8px'
            }}>
              <MetricRow label="Current EPS" value={valuation.eps0 ? `$${valuation.eps0.toFixed(2)}` : 'N/A'} />
              <MetricRow label="Growth Rate Used" value={valuation.g ? `${(valuation.g * 100).toFixed(1)}%` : 'N/A'} />
              <MetricRow label="Future EPS (10yr)" value={valuation.future_eps ? `$${valuation.future_eps.toFixed(2)}` : 'N/A'} />
              <MetricRow label="PE Ratio Used" value={valuation.pe_used ? `${valuation.pe_used.toFixed(1)}x` : 'N/A'} />
              <MetricRow label="Future Price" value={valuation.future_price ? `$${valuation.future_price.toFixed(2)}` : 'N/A'} />
              <MetricRow label="Owner Earnings" value={valuation.owner_earnings ? `$${(valuation.owner_earnings / 1e6).toFixed(1)}M` : 'N/A'} />
            </div>
          </details>

          {/* Raw JSON (collapsed) */}
          <details>
            <summary style={{
              cursor: 'pointer',
              padding: '12px 16px',
              background: '#f9fafb',
              borderRadius: 8,
              fontWeight: 600,
              color: '#374151'
            }}>
              View Raw JSON Response
            </summary>
            <pre style={{
              background: '#f6f6f6',
              padding: 16,
              borderRadius: '0 0 8px 8px',
              overflow: 'auto',
              fontSize: 12
            }}>
              {JSON.stringify(valuation, null, 2)}
            </pre>
          </details>
        </div>
      )}

      {/* Educational Content */}
      {!valuation && (
        <div style={{
          padding: 20,
          background: '#f0f9ff',
          border: '1px solid #bae6fd',
          borderRadius: 12
        }}>
          <h4 style={{ margin: '0 0 12px', color: '#0369a1' }}>Understanding Rule #1 Valuation</h4>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16 }}>
            <div>
              <strong>🏷️ Sticker Price</strong>
              <p style={{ margin: '4px 0 0', fontSize: 13, color: '#0c4a6e' }}>
                The true value of the company based on projected future earnings, discounted back to today.
              </p>
            </div>
            <div>
              <strong>🎯 MOS Price</strong>
              <p style={{ margin: '4px 0 0', fontSize: 13, color: '#0c4a6e' }}>
                Your maximum buy price — Sticker Price minus your Margin of Safety discount.
              </p>
            </div>
            <div>
              <strong>💰 Ten Cap</strong>
              <p style={{ margin: '4px 0 0', fontSize: 13, color: '#0c4a6e' }}>
                Price at which you&apos;d earn 10% return from owner earnings alone (like buying a rental property).
              </p>
            </div>
            <div>
              <strong>⏱️ Payback Time</strong>
              <p style={{ margin: '4px 0 0', fontSize: 13, color: '#0c4a6e' }}>
                Years for the company&apos;s owner earnings to pay back your investment. Target: 8 years or less.
              </p>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}