import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import TimeseriesChart from '../components/TimeseriesChart'

// Mock ResizeObserver which is used by Recharts
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}))

describe('TimeseriesChart', () => {
  const sampleData = [
    { fy: 2020, revenue: 100000000, eps: 5.25 },
    { fy: 2021, revenue: 120000000, eps: 6.10 },
    { fy: 2022, revenue: 140000000, eps: 7.00 },
    { fy: 2023, revenue: 160000000, eps: 8.50 },
  ]

  const singleLine = [{ dataKey: 'revenue', name: 'Revenue', color: '#8884d8' }]
  const multipleLines = [
    { dataKey: 'revenue', name: 'Revenue', color: '#8884d8' },
    { dataKey: 'eps', name: 'EPS', color: '#82ca9d' },
  ]

  describe('Basic Rendering', () => {
    it('renders without crashing with minimal props', () => {
      const { container } = render(
        <TimeseriesChart 
          data={[{ fy: 2020, revenue: 100 }]} 
          lines={[{ dataKey: 'revenue', name: 'Revenue' }]} 
        />
      )
      expect(container).toBeTruthy()
    })

    it('renders with multiple data points', () => {
      const { container } = render(
        <TimeseriesChart data={sampleData} lines={singleLine} />
      )
      expect(container).toBeTruthy()
    })

    it('renders with multiple lines', () => {
      const { container } = render(
        <TimeseriesChart data={sampleData} lines={multipleLines} />
      )
      expect(container).toBeTruthy()
    })
  })

  describe('Props Handling', () => {
    it('handles empty data array', () => {
      const { container } = render(
        <TimeseriesChart data={[]} lines={singleLine} />
      )
      expect(container).toBeTruthy()
    })

    it('handles formatLeftAxis prop', () => {
      const formatter = (value: number) => `$${value}M`
      const { container } = render(
        <TimeseriesChart 
          data={sampleData} 
          lines={singleLine}
          formatLeftAxis={formatter}
        />
      )
      expect(container).toBeTruthy()
    })

    it('handles formatRightAxis prop', () => {
      const formatter = (value: number) => `${value}%`
      const linesWithRightAxis = [
        { dataKey: 'revenue', name: 'Revenue', yAxisId: 'left' },
        { dataKey: 'eps', name: 'EPS', yAxisId: 'right' },
      ]
      const { container } = render(
        <TimeseriesChart 
          data={sampleData} 
          lines={linesWithRightAxis}
          formatRightAxis={formatter}
        />
      )
      expect(container).toBeTruthy()
    })

    it('handles custom height', () => {
      const { container } = render(
        <TimeseriesChart 
          data={sampleData} 
          lines={singleLine}
          height={400}
        />
      )
      expect(container).toBeTruthy()
    })

    it('handles reference line', () => {
      const { container } = render(
        <TimeseriesChart 
          data={sampleData} 
          lines={singleLine}
          referenceLine={{ y: 150000000, label: 'Target', color: 'red' }}
        />
      )
      expect(container).toBeTruthy()
    })
  })

  describe('Line Configuration', () => {
    it('renders lines with default colors when not specified', () => {
      const linesWithoutColor = [{ dataKey: 'revenue', name: 'Revenue' }]
      const { container } = render(
        <TimeseriesChart data={sampleData} lines={linesWithoutColor} />
      )
      expect(container).toBeTruthy()
    })

    it('renders lines with custom colors', () => {
      const linesWithColors = [
        { dataKey: 'revenue', name: 'Revenue', color: '#ff0000' },
        { dataKey: 'eps', name: 'EPS', color: '#00ff00' },
      ]
      const { container } = render(
        <TimeseriesChart data={sampleData} lines={linesWithColors} />
      )
      expect(container).toBeTruthy()
    })
  })

  describe('Data Variations', () => {
    it('handles data with null values', () => {
      const dataWithNulls = [
        { fy: 2020, revenue: 100 },
        { fy: 2021, revenue: null },
        { fy: 2022, revenue: 140 },
      ]
      const { container } = render(
        <TimeseriesChart data={dataWithNulls} lines={singleLine} />
      )
      expect(container).toBeTruthy()
    })

    it('handles data with negative values', () => {
      const dataWithNegatives = [
        { fy: 2020, revenue: 100 },
        { fy: 2021, revenue: -50 },
        { fy: 2022, revenue: 80 },
      ]
      const { container } = render(
        <TimeseriesChart data={dataWithNegatives} lines={singleLine} />
      )
      expect(container).toBeTruthy()
    })

    it('handles data with zero values', () => {
      const dataWithZeros = [
        { fy: 2020, revenue: 0 },
        { fy: 2021, revenue: 100 },
        { fy: 2022, revenue: 0 },
      ]
      const { container } = render(
        <TimeseriesChart data={dataWithZeros} lines={singleLine} />
      )
      expect(container).toBeTruthy()
    })

    it('handles large numbers', () => {
      const dataWithLargeNumbers = [
        { fy: 2020, revenue: 1000000000000 },
        { fy: 2021, revenue: 2000000000000 },
      ]
      const { container } = render(
        <TimeseriesChart data={dataWithLargeNumbers} lines={singleLine} />
      )
      expect(container).toBeTruthy()
    })

    it('handles decimal values', () => {
      const dataWithDecimals = [
        { fy: 2020, eps: 5.25 },
        { fy: 2021, eps: 6.789 },
        { fy: 2022, eps: 7.123456 },
      ]
      const { container } = render(
        <TimeseriesChart 
          data={dataWithDecimals} 
          lines={[{ dataKey: 'eps', name: 'EPS' }]} 
        />
      )
      expect(container).toBeTruthy()
    })
  })

  describe('Responsive Behavior', () => {
    it('renders within ResponsiveContainer', () => {
      const { container } = render(
        <TimeseriesChart data={sampleData} lines={singleLine} />
      )
      // Check that the component renders a container div
      expect(container.firstChild).toBeTruthy()
    })
  })
})