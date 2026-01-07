import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'

// Mock fetch globally
const mockFetch = vi.fn()
global.fetch = mockFetch

// Import after mocking
import BigFivePanel from '../components/BigFivePanel'

describe('BigFivePanel', () => {
  beforeEach(() => {
    mockFetch.mockReset()
  })

  describe('Loading State', () => {
    it('shows loading message initially', () => {
      mockFetch.mockImplementation(() => new Promise(() => {})) // Never resolves
      render(<BigFivePanel api="http://localhost:8000" ticker="MSFT" />)
      expect(screen.getByText('Loading metrics...')).toBeInTheDocument()
    })

    it('displays section title while loading', () => {
      mockFetch.mockImplementation(() => new Promise(() => {}))
      render(<BigFivePanel api="http://localhost:8000" ticker="MSFT" />)
      expect(screen.getByText('The Big Five Numbers')).toBeInTheDocument()
    })
  })

  describe('Error State', () => {
    it('shows error message on fetch failure', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'))
      render(<BigFivePanel api="http://localhost:8000" ticker="MSFT" />)
      
      await waitFor(() => {
        expect(screen.getByText(/Error:/)).toBeInTheDocument()
      })
    })

    it('shows error when response is not ok', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
      })
      render(<BigFivePanel api="http://localhost:8000" ticker="MSFT" />)
      
      await waitFor(() => {
        expect(screen.getByText(/Error:/)).toBeInTheDocument()
      })
    })
  })

  describe('Success State', () => {
    const mockMetrics = {
      roic_avg_10y: 0.18,
      growths: {
        rev_cagr_5y: 0.12,
        rev_cagr_10y: 0.11,
        eps_cagr_5y: 0.15,
        eps_cagr_10y: 0.13,
      },
      fcf_growth: 0.08,
      debt_to_equity: 0.35,
      interest_coverage: 15.5,
    }

    it('renders all Big Five cards on success', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockMetrics),
      })
      render(<BigFivePanel api="http://localhost:8000" ticker="MSFT" />)
      
      await waitFor(() => {
        expect(screen.getByText('ROIC')).toBeInTheDocument()
        expect(screen.getByText('Revenue Growth')).toBeInTheDocument()
        expect(screen.getByText('EPS Growth')).toBeInTheDocument()
        expect(screen.getByText('Free Cash Flow')).toBeInTheDocument()
        expect(screen.getByText('Debt Level')).toBeInTheDocument()
      })
    })

    it('displays overall score', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockMetrics),
      })
      render(<BigFivePanel api="http://localhost:8000" ticker="MSFT" />)
      
      await waitFor(() => {
        expect(screen.getByText('Metrics Passing')).toBeInTheDocument()
      })
    })

    it('displays educational summary', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockMetrics),
      })
      render(<BigFivePanel api="http://localhost:8000" ticker="MSFT" />)
      
      await waitFor(() => {
        expect(screen.getByText('Understanding the Big Five')).toBeInTheDocument()
      })
    })

    it('fetches data with correct URL', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockMetrics),
      })
      render(<BigFivePanel api="http://localhost:8000" ticker="AAPL" />)
      
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith('http://localhost:8000/api/v1/company/AAPL/metrics')
      })
    })
  })

  describe('Metric Status Logic', () => {
    it('shows N/A for missing metrics', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({}),
      })
      render(<BigFivePanel api="http://localhost:8000" ticker="MSFT" />)
      
      await waitFor(() => {
        const naElements = screen.getAllByText('N/A')
        expect(naElements.length).toBeGreaterThan(0)
      })
    })
  })
})

// Unit tests for helper functions (extracted from component)
describe('Helper Functions', () => {
  describe('getMetricStatus', () => {
    // Re-implement the function for testing
    function getMetricStatus(
      value: number | null | undefined,
      target: number,
      higherIsBetter = true
    ): { color: string; label: string; bg: string; icon: string } {
      if (value === null || value === undefined) {
        return { color: '#6b7280', label: 'No Data', bg: '#f3f4f6', icon: '—' }
      }
      
      const ratio = higherIsBetter ? value / target : target / value
      
      if (ratio >= 1.2) return { color: '#15803d', label: 'Excellent', bg: '#dcfce7', icon: '✓' }
      if (ratio >= 1.0) return { color: '#65a30d', label: 'Good', bg: '#ecfccb', icon: '✓' }
      if (ratio >= 0.8) return { color: '#ca8a04', label: 'Fair', bg: '#fef9c3', icon: '~' }
      if (ratio >= 0.6) return { color: '#ea580c', label: 'Weak', bg: '#ffedd5', icon: '!' }
      return { color: '#dc2626', label: 'Poor', bg: '#fee2e2', icon: '✗' }
    }

    it('returns No Data for null value', () => {
      const result = getMetricStatus(null, 0.15)
      expect(result.label).toBe('No Data')
      expect(result.icon).toBe('—')
    })

    it('returns No Data for undefined value', () => {
      const result = getMetricStatus(undefined, 0.15)
      expect(result.label).toBe('No Data')
    })

    it('returns Excellent for value >= 1.2x target (higher is better)', () => {
      const result = getMetricStatus(0.20, 0.15) // 0.20/0.15 = 1.33
      expect(result.label).toBe('Excellent')
      expect(result.icon).toBe('✓')
    })

    it('returns Good for value >= 1.0x target (higher is better)', () => {
      const result = getMetricStatus(0.16, 0.15) // 0.16/0.15 = 1.07
      expect(result.label).toBe('Good')
    })

    it('returns Fair for value >= 0.8x target (higher is better)', () => {
      const result = getMetricStatus(0.13, 0.15) // 0.13/0.15 = 0.87
      expect(result.label).toBe('Fair')
      expect(result.icon).toBe('~')
    })

    it('returns Weak for value >= 0.6x target (higher is better)', () => {
      const result = getMetricStatus(0.10, 0.15) // 0.10/0.15 = 0.67
      expect(result.label).toBe('Weak')
      expect(result.icon).toBe('!')
    })

    it('returns Poor for value < 0.6x target (higher is better)', () => {
      const result = getMetricStatus(0.05, 0.15) // 0.05/0.15 = 0.33
      expect(result.label).toBe('Poor')
      expect(result.icon).toBe('✗')
    })

    it('handles lower is better correctly (debt ratio)', () => {
      // For debt, lower is better: target/value
      const result = getMetricStatus(0.3, 0.5, false) // 0.5/0.3 = 1.67 (excellent)
      expect(result.label).toBe('Excellent')
    })

    it('handles poor debt ratio correctly', () => {
      const result = getMetricStatus(1.0, 0.5, false) // 0.5/1.0 = 0.5 (poor)
      expect(result.label).toBe('Poor')
    })
  })

  describe('formatPct', () => {
    function formatPct(value: number | null | undefined, decimals = 1): string {
      if (value === null || value === undefined) return 'N/A'
      return `${(value * 100).toFixed(decimals)}%`
    }

    it('returns N/A for null', () => {
      expect(formatPct(null)).toBe('N/A')
    })

    it('returns N/A for undefined', () => {
      expect(formatPct(undefined)).toBe('N/A')
    })

    it('formats decimal as percentage', () => {
      expect(formatPct(0.15)).toBe('15.0%')
    })

    it('respects decimal places parameter', () => {
      expect(formatPct(0.1567, 2)).toBe('15.67%')
    })

    it('handles zero correctly', () => {
      expect(formatPct(0)).toBe('0.0%')
    })

    it('handles negative values', () => {
      expect(formatPct(-0.05)).toBe('-5.0%')
    })
  })

  describe('formatCurrency', () => {
    function formatCurrency(value: number | null | undefined): string {
      if (value === null || value === undefined) return 'N/A'
      if (Math.abs(value) >= 1e9) return `$${(value / 1e9).toFixed(1)}B`
      if (Math.abs(value) >= 1e6) return `$${(value / 1e6).toFixed(1)}M`
      return `$${value.toFixed(0)}`
    }

    it('returns N/A for null', () => {
      expect(formatCurrency(null)).toBe('N/A')
    })

    it('returns N/A for undefined', () => {
      expect(formatCurrency(undefined)).toBe('N/A')
    })

    it('formats billions correctly', () => {
      expect(formatCurrency(5_000_000_000)).toBe('$5.0B')
    })

    it('formats millions correctly', () => {
      expect(formatCurrency(250_000_000)).toBe('$250.0M')
    })

    it('formats smaller values correctly', () => {
      expect(formatCurrency(50000)).toBe('$50000')
    })

    it('handles negative billions', () => {
      expect(formatCurrency(-2_500_000_000)).toBe('$-2.5B')
    })
  })
})
