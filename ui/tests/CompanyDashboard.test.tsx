import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import CompanyDashboard from '../components/CompanyDashboard'

// Mock ResizeObserver for Recharts
class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
global.ResizeObserver = ResizeObserver

const API_BASE = 'http://localhost:8000'

describe('CompanyDashboard', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Initial Render', () => {
    it('renders the dashboard with title', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce({
        json: () => Promise.resolve({ is: [], roic: [], coverage: [] })
      })

      render(<CompanyDashboard api={API_BASE} ticker="AAPL" />)
      
      await waitFor(() => {
        expect(screen.getByText('Historical Trends')).toBeInTheDocument()
      })
    })

    it('shows loading state initially', () => {
      global.fetch = vi.fn().mockImplementation(() => 
        new Promise(resolve => setTimeout(() => resolve({
          json: () => Promise.resolve({ is: [], roic: [], coverage: [] })
        }), 100))
      )

      render(<CompanyDashboard api={API_BASE} ticker="AAPL" />)
      
      expect(screen.getByText('Loading historical data...')).toBeInTheDocument()
    })

    it('displays description text', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce({
        json: () => Promise.resolve({ is: [], roic: [], coverage: [] })
      })

      render(<CompanyDashboard api={API_BASE} ticker="AAPL" />)
      
      await waitFor(() => {
        expect(screen.getByText(/Track key financial metrics over time/)).toBeInTheDocument()
      })
    })
  })

  describe('Data Fetching', () => {
    it('fetches timeseries data on mount', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce({
        json: () => Promise.resolve({ is: [], roic: [], coverage: [] })
      })

      render(<CompanyDashboard api={API_BASE} ticker="AAPL" />)
      
      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(`${API_BASE}/api/v1/company/AAPL/timeseries`)
      })
    })

    it('handles fetch error gracefully', async () => {
      global.fetch = vi.fn().mockRejectedValueOnce(new Error('Network error'))

      render(<CompanyDashboard api={API_BASE} ticker="AAPL" />)
      
      await waitFor(() => {
        expect(screen.getByText(/Error loading charts/)).toBeInTheDocument()
      })
    })

    it('refetches when ticker changes', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        json: () => Promise.resolve({ is: [], roic: [], coverage: [] })
      })

      const { rerender } = render(<CompanyDashboard api={API_BASE} ticker="AAPL" />)
      
      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(`${API_BASE}/api/v1/company/AAPL/timeseries`)
      })

      rerender(<CompanyDashboard api={API_BASE} ticker="MSFT" />)
      
      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(`${API_BASE}/api/v1/company/MSFT/timeseries`)
      })
    })
  })

  describe('Chart Cards', () => {
    it('renders Revenue & EPS chart card', async () => {
      const mockData = {
        is: [
          { fy: 2020, revenue: 100000000000, eps: 3.5 },
          { fy: 2021, revenue: 120000000000, eps: 4.2 }
        ],
        roic: [],
        coverage: []
      }

      global.fetch = vi.fn().mockResolvedValueOnce({
        json: () => Promise.resolve(mockData)
      })

      render(<CompanyDashboard api={API_BASE} ticker="AAPL" />)
      
      await waitFor(() => {
        expect(screen.getByText('Revenue & EPS')).toBeInTheDocument()
      })
    })

    it('renders ROIC chart card', async () => {
      const mockData = {
        is: [],
        roic: [
          { fy: 2020, roic: 0.18 },
          { fy: 2021, roic: 0.22 }
        ],
        coverage: []
      }

      global.fetch = vi.fn().mockResolvedValueOnce({
        json: () => Promise.resolve(mockData)
      })

      render(<CompanyDashboard api={API_BASE} ticker="AAPL" />)
      
      await waitFor(() => {
        expect(screen.getByText('Return on Invested Capital (ROIC)')).toBeInTheDocument()
      })
    })

    it('renders Interest Coverage chart card', async () => {
      const mockData = {
        is: [],
        roic: [],
        coverage: [
          { fy: 2020, coverage: 8.5 },
          { fy: 2021, coverage: 9.2 }
        ]
      }

      global.fetch = vi.fn().mockResolvedValueOnce({
        json: () => Promise.resolve(mockData)
      })

      render(<CompanyDashboard api={API_BASE} ticker="AAPL" />)
      
      await waitFor(() => {
        expect(screen.getByText('Interest Coverage Ratio')).toBeInTheDocument()
      })
    })

    it('shows no data message when data is empty', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce({
        json: () => Promise.resolve({ is: [], roic: [], coverage: [] })
      })

      render(<CompanyDashboard api={API_BASE} ticker="AAPL" />)
      
      await waitFor(() => {
        expect(screen.getByText('No revenue/EPS data available')).toBeInTheDocument()
        expect(screen.getByText('No ROIC data available')).toBeInTheDocument()
        expect(screen.getByText('No interest coverage data available')).toBeInTheDocument()
      })
    })
  })

  describe('ROIC Insights', () => {
    it('displays latest ROIC value', async () => {
      const mockData = {
        is: [],
        roic: [
          { fy: 2020, roic: 0.15 },
          { fy: 2021, roic: 0.18 }
        ],
        coverage: []
      }

      global.fetch = vi.fn().mockResolvedValueOnce({
        json: () => Promise.resolve(mockData)
      })

      render(<CompanyDashboard api={API_BASE} ticker="AAPL" />)
      
      await waitFor(() => {
        expect(screen.getByText('Latest ROIC')).toBeInTheDocument()
        expect(screen.getByText('18.0%')).toBeInTheDocument()
      })
    })

    it('displays average ROIC value', async () => {
      const mockData = {
        is: [],
        roic: [
          { fy: 2020, roic: 0.14 },
          { fy: 2021, roic: 0.16 }
        ],
        coverage: []
      }

      global.fetch = vi.fn().mockResolvedValueOnce({
        json: () => Promise.resolve(mockData)
      })

      render(<CompanyDashboard api={API_BASE} ticker="AAPL" />)
      
      await waitFor(() => {
        expect(screen.getByText('Average ROIC')).toBeInTheDocument()
        expect(screen.getByText('15.0%')).toBeInTheDocument()
      })
    })

    it('shows improving trend when ROIC increases', async () => {
      const mockData = {
        is: [],
        roic: [
          { fy: 2020, roic: 0.12 },
          { fy: 2021, roic: 0.18 }
        ],
        coverage: []
      }

      global.fetch = vi.fn().mockResolvedValueOnce({
        json: () => Promise.resolve(mockData)
      })

      render(<CompanyDashboard api={API_BASE} ticker="AAPL" />)
      
      await waitFor(() => {
        expect(screen.getByText(/improving/)).toBeInTheDocument()
      })
    })

    it('shows declining trend when ROIC decreases', async () => {
      const mockData = {
        is: [],
        roic: [
          { fy: 2020, roic: 0.20 },
          { fy: 2021, roic: 0.15 }
        ],
        coverage: []
      }

      global.fetch = vi.fn().mockResolvedValueOnce({
        json: () => Promise.resolve(mockData)
      })

      render(<CompanyDashboard api={API_BASE} ticker="AAPL" />)
      
      await waitFor(() => {
        expect(screen.getByText(/declining/)).toBeInTheDocument()
      })
    })
  })

  describe('Educational Content', () => {
    it('shows educational tips for Revenue & EPS', async () => {
      const mockData = {
        is: [{ fy: 2021, revenue: 100000000000, eps: 5 }],
        roic: [],
        coverage: []
      }

      global.fetch = vi.fn().mockResolvedValueOnce({
        json: () => Promise.resolve(mockData)
      })

      render(<CompanyDashboard api={API_BASE} ticker="AAPL" />)
      
      await waitFor(() => {
        expect(screen.getByText(/Look for consistent upward trends/)).toBeInTheDocument()
      })
    })

    it('shows educational tips for Interest Coverage', async () => {
      const mockData = {
        is: [],
        roic: [],
        coverage: [{ fy: 2021, coverage: 8 }]
      }

      global.fetch = vi.fn().mockResolvedValueOnce({
        json: () => Promise.resolve(mockData)
      })

      render(<CompanyDashboard api={API_BASE} ticker="AAPL" />)
      
      await waitFor(() => {
        expect(screen.getByText(/Target: ≥5x coverage/)).toBeInTheDocument()
      })
    })

    it('shows no data warning when all data is empty', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce({
        json: () => Promise.resolve({ is: [], roic: [], coverage: [] })
      })

      render(<CompanyDashboard api={API_BASE} ticker="AAPL" />)
      
      await waitFor(() => {
        expect(screen.getByText('No Historical Data Available')).toBeInTheDocument()
      })
    })
  })

  describe('InfoTip Component', () => {
    it('renders info tooltips for chart descriptions', async () => {
      const mockData = {
        is: [{ fy: 2021, revenue: 100000000000, eps: 5 }],
        roic: [],
        coverage: []
      }

      global.fetch = vi.fn().mockResolvedValueOnce({
        json: () => Promise.resolve(mockData)
      })

      render(<CompanyDashboard api={API_BASE} ticker="AAPL" />)
      
      await waitFor(() => {
        // InfoTip renders as "?" spans
        const infoTips = screen.getAllByText('?')
        expect(infoTips.length).toBeGreaterThan(0)
      })
    })
  })

  describe('Data Transformation', () => {
    it('transforms ROIC data correctly', async () => {
      const mockData = {
        is: [],
        roic: [
          { fy: 2020, roic: 0.156 },
          { fy: 2021, roic: 0.189 }
        ],
        coverage: []
      }

      global.fetch = vi.fn().mockResolvedValueOnce({
        json: () => Promise.resolve(mockData)
      })

      render(<CompanyDashboard api={API_BASE} ticker="AAPL" />)
      
      await waitFor(() => {
        expect(screen.getByText('18.9%')).toBeInTheDocument()
      })
    })

    it('handles null ROIC values', async () => {
      const mockData = {
        is: [],
        roic: [
          { fy: 2020, roic: null },
          { fy: 2021, roic: 0.15 }
        ],
        coverage: []
      }

      global.fetch = vi.fn().mockResolvedValueOnce({
        json: () => Promise.resolve(mockData)
      })

      render(<CompanyDashboard api={API_BASE} ticker="AAPL" />)
      
      await waitFor(() => {
        expect(screen.getByText('Return on Invested Capital (ROIC)')).toBeInTheDocument()
      })
    })
  })
})
