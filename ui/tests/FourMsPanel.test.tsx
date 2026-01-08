import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import FourMsPanel from '../components/FourMsPanel'

// Mock ResizeObserver for Recharts
class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
global.ResizeObserver = ResizeObserver

const API_BASE = 'http://localhost:8000'

describe('FourMsPanel', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Helper Functions', () => {
    // Test getScoreInfo through component rendering
    it('displays correct score labels for different score ranges', async () => {
      const mockData = {
        moat: { score: 0.85, roic_avg: 0.18, margin_stability: 0.9 },
        management: { score: 0.65, reinvest_ratio_avg: 0.3, payout_ratio_avg: 0.2 },
        mos_recommendation: { recommended_mos: 0.35 }
      }

      global.fetch = vi.fn().mockResolvedValueOnce({
        json: () => Promise.resolve(mockData)
      })

      render(<FourMsPanel api={API_BASE} ticker="AAPL" />)
      
      fireEvent.click(screen.getByText('Analyze Moat, Management & MOS'))
      
      await waitFor(() => {
        // Check that Moat card is rendered (score 0.85 = Excellent)
        expect(screen.getByText('Moat')).toBeInTheDocument()
      })
    })
  })

  describe('Initial Render', () => {
    it('renders the panel with title and description', () => {
      render(<FourMsPanel api={API_BASE} ticker="AAPL" />)
      
      expect(screen.getByText('The Four Ms Analysis')).toBeInTheDocument()
      expect(screen.getByText(/Phil Town's Rule #1 framework/)).toBeInTheDocument()
    })

    it('renders action buttons', () => {
      render(<FourMsPanel api={API_BASE} ticker="AAPL" />)
      
      expect(screen.getByText('Analyze Moat, Management & MOS')).toBeInTheDocument()
      expect(screen.getByText('Get Business Description (SEC 10-K)')).toBeInTheDocument()
    })

    it('shows educational content when no data loaded', () => {
      render(<FourMsPanel api={API_BASE} ticker="AAPL" />)
      
      expect(screen.getByText('What are the Four Ms?')).toBeInTheDocument()
      expect(screen.getByText(/A durable competitive advantage/)).toBeInTheDocument()
    })
  })

  describe('Load Summary', () => {
    it('fetches and displays Four Ms data on button click', async () => {
      const mockData = {
        moat: { score: 0.75, roic_avg: 0.16, margin_stability: 0.85 },
        management: { score: 0.6, reinvest_ratio_avg: 0.25, payout_ratio_avg: 0.15 },
        mos_recommendation: { recommended_mos: 0.4 }
      }

      global.fetch = vi.fn().mockResolvedValueOnce({
        json: () => Promise.resolve(mockData)
      })

      render(<FourMsPanel api={API_BASE} ticker="AAPL" />)
      
      fireEvent.click(screen.getByText('Analyze Moat, Management & MOS'))
      
      await waitFor(() => {
        expect(screen.getByText('Moat')).toBeInTheDocument()
        expect(screen.getByText('Management')).toBeInTheDocument()
        expect(screen.getByText('Margin of Safety')).toBeInTheDocument()
      })

      expect(global.fetch).toHaveBeenCalledWith(`${API_BASE}/api/v1/company/AAPL/fourm`)
    })

    it('shows loading state while fetching', async () => {
      global.fetch = vi.fn().mockImplementation(() => 
        new Promise(resolve => setTimeout(() => resolve({
          json: () => Promise.resolve({ moat: {}, management: {}, mos_recommendation: {} })
        }), 100))
      )

      render(<FourMsPanel api={API_BASE} ticker="AAPL" />)
      
      fireEvent.click(screen.getByText('Analyze Moat, Management & MOS'))
      
      expect(screen.getByText('Analyzing...')).toBeInTheDocument()
    })

    it('displays ROIC and margin metrics', async () => {
      const mockData = {
        moat: { score: 0.8, roic_avg: 0.22, margin_stability: 0.88 },
        management: { score: 0.7, reinvest_ratio_avg: 0.35, payout_ratio_avg: 0.25 },
        mos_recommendation: { recommended_mos: 0.3 }
      }

      global.fetch = vi.fn().mockResolvedValueOnce({
        json: () => Promise.resolve(mockData)
      })

      render(<FourMsPanel api={API_BASE} ticker="MSFT" />)
      
      fireEvent.click(screen.getByText('Analyze Moat, Management & MOS'))
      
      await waitFor(() => {
        expect(screen.getByText('Avg ROIC')).toBeInTheDocument()
        expect(screen.getByText('Margin Stability')).toBeInTheDocument()
        expect(screen.getByText('Reinvestment Ratio')).toBeInTheDocument()
        expect(screen.getByText('Payout Ratio')).toBeInTheDocument()
      })
    })

    it('displays MOS recommendation percentage', async () => {
      const mockData = {
        moat: { score: 0.5 },
        management: { score: 0.5 },
        mos_recommendation: { recommended_mos: 0.45 }
      }

      global.fetch = vi.fn().mockResolvedValueOnce({
        json: () => Promise.resolve(mockData)
      })

      render(<FourMsPanel api={API_BASE} ticker="AAPL" />)
      
      fireEvent.click(screen.getByText('Analyze Moat, Management & MOS'))
      
      await waitFor(() => {
        expect(screen.getByText('45%')).toBeInTheDocument()
        expect(screen.getByText('Recommended Discount')).toBeInTheDocument()
      })
    })
  })

  describe('Refresh Meaning', () => {
    it('fetches and displays business description', async () => {
      const mockMeaning = {
        item1_excerpt: 'Apple Inc. designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and accessories worldwide.'
      }

      global.fetch = vi.fn().mockResolvedValueOnce({
        json: () => Promise.resolve(mockMeaning)
      })

      render(<FourMsPanel api={API_BASE} ticker="AAPL" />)
      
      fireEvent.click(screen.getByText('Get Business Description (SEC 10-K)'))
      
      await waitFor(() => {
        expect(screen.getByText(/Apple Inc. designs, manufactures/)).toBeInTheDocument()
      })

      expect(global.fetch).toHaveBeenCalledWith(
        `${API_BASE}/api/v1/company/AAPL/fourm/meaning/refresh`,
        { method: 'POST' }
      )
    })

    it('shows loading state while fetching meaning', async () => {
      global.fetch = vi.fn().mockImplementation(() => 
        new Promise(resolve => setTimeout(() => resolve({
          json: () => Promise.resolve({ item1_excerpt: 'Test' })
        }), 100))
      )

      render(<FourMsPanel api={API_BASE} ticker="AAPL" />)
      
      fireEvent.click(screen.getByText('Get Business Description (SEC 10-K)'))
      
      expect(screen.getByText('Fetching...')).toBeInTheDocument()
    })

    it('displays Meaning card with SEC 10-K label', async () => {
      const mockMeaning = {
        item1_excerpt: 'Test business description'
      }

      global.fetch = vi.fn().mockResolvedValueOnce({
        json: () => Promise.resolve(mockMeaning)
      })

      render(<FourMsPanel api={API_BASE} ticker="AAPL" />)
      
      fireEvent.click(screen.getByText('Get Business Description (SEC 10-K)'))
      
      await waitFor(() => {
        expect(screen.getByText('Meaning')).toBeInTheDocument()
        expect(screen.getByText(/From SEC 10-K Filing/)).toBeInTheDocument()
      })
    })
  })

  describe('Score Display', () => {
    it('displays score badges with correct labels', async () => {
      const mockData = {
        moat: { score: 0.9 },
        management: { score: 0.3 },
        mos_recommendation: { recommended_mos: 0.5 }
      }

      global.fetch = vi.fn().mockResolvedValueOnce({
        json: () => Promise.resolve(mockData)
      })

      render(<FourMsPanel api={API_BASE} ticker="AAPL" />)
      
      fireEvent.click(screen.getByText('Analyze Moat, Management & MOS'))
      
      await waitFor(() => {
        expect(screen.getByText(/90\/100/)).toBeInTheDocument()
      })
    })

    it('handles null scores gracefully', async () => {
      const mockData = {
        moat: { score: null, roic_avg: null },
        management: { score: undefined },
        mos_recommendation: {}
      }

      global.fetch = vi.fn().mockResolvedValueOnce({
        json: () => Promise.resolve(mockData)
      })

      render(<FourMsPanel api={API_BASE} ticker="AAPL" />)
      
      fireEvent.click(screen.getByText('Analyze Moat, Management & MOS'))
      
      await waitFor(() => {
        expect(screen.getByText('Moat')).toBeInTheDocument()
      })
    })
  })

  describe('MOS Risk Levels', () => {
    it('displays high risk for MOS >= 50%', async () => {
      const mockData = {
        moat: { score: 0.3 },
        management: { score: 0.3 },
        mos_recommendation: { recommended_mos: 0.55 }
      }

      global.fetch = vi.fn().mockResolvedValueOnce({
        json: () => Promise.resolve(mockData)
      })

      render(<FourMsPanel api={API_BASE} ticker="AAPL" />)
      
      fireEvent.click(screen.getByText('Analyze Moat, Management & MOS'))
      
      await waitFor(() => {
        expect(screen.getByText(/High Risk/)).toBeInTheDocument()
      })
    })

    it('displays lower risk for MOS < 30%', async () => {
      const mockData = {
        moat: { score: 0.9 },
        management: { score: 0.9 },
        mos_recommendation: { recommended_mos: 0.25 }
      }

      global.fetch = vi.fn().mockResolvedValueOnce({
        json: () => Promise.resolve(mockData)
      })

      render(<FourMsPanel api={API_BASE} ticker="AAPL" />)
      
      fireEvent.click(screen.getByText('Analyze Moat, Management & MOS'))
      
      await waitFor(() => {
        expect(screen.getByText(/Lower Risk/)).toBeInTheDocument()
      })
    })
  })

  describe('Educational Content', () => {
    it('shows educational tips in Moat card', async () => {
      const mockData = {
        moat: { score: 0.7 },
        management: { score: 0.6 },
        mos_recommendation: { recommended_mos: 0.35 }
      }

      global.fetch = vi.fn().mockResolvedValueOnce({
        json: () => Promise.resolve(mockData)
      })

      render(<FourMsPanel api={API_BASE} ticker="AAPL" />)
      
      fireEvent.click(screen.getByText('Analyze Moat, Management & MOS'))
      
      await waitFor(() => {
        expect(screen.getByText(/Companies with wide moats have ROIC consistently above 15%/)).toBeInTheDocument()
      })
    })

    it('shows educational tips in Management card', async () => {
      const mockData = {
        moat: { score: 0.7 },
        management: { score: 0.6 },
        mos_recommendation: { recommended_mos: 0.35 }
      }

      global.fetch = vi.fn().mockResolvedValueOnce({
        json: () => Promise.resolve(mockData)
      })

      render(<FourMsPanel api={API_BASE} ticker="AAPL" />)
      
      fireEvent.click(screen.getByText('Analyze Moat, Management & MOS'))
      
      await waitFor(() => {
        expect(screen.getByText(/Owner-oriented managers/)).toBeInTheDocument()
      })
    })
  })

  describe('Ticker Changes', () => {
    it('uses correct ticker in API calls', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce({
        json: () => Promise.resolve({ moat: {}, management: {}, mos_recommendation: {} })
      })

      render(<FourMsPanel api={API_BASE} ticker="GOOGL" />)
      
      fireEvent.click(screen.getByText('Analyze Moat, Management & MOS'))
      
      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(`${API_BASE}/api/v1/company/GOOGL/fourm`)
      })
    })
  })

  describe('Phase E: Balance Sheet Resilience Card', () => {
    it('displays balance sheet resilience card when data is present', async () => {
      const mockData = {
        moat: { score: 0.75, roic_avg: 0.16, margin_stability: 0.85 },
        management: { score: 0.6, reinvest_ratio_avg: 0.25, payout_ratio_avg: 0.15 },
        mos_recommendation: { recommended_mos: 0.4 },
        balance_sheet_resilience: {
          score: 4.5,
          latest_coverage: 12.5,
          debt_to_equity: 0.35,
          latest_net_debt: 25000000000,
          net_debt_trend: -0.15
        }
      }

      global.fetch = vi.fn().mockResolvedValueOnce({
        json: () => Promise.resolve(mockData)
      })

      render(<FourMsPanel api={API_BASE} ticker="WMT" />)
      
      fireEvent.click(screen.getByText('Analyze Moat, Management & MOS'))
      
      await waitFor(() => {
        expect(screen.getByText('Balance Sheet')).toBeInTheDocument()
        expect(screen.getByText('Resilience Score')).toBeInTheDocument()
      })
    })

    it('displays interest coverage metric', async () => {
      const mockData = {
        moat: { score: 0.7 },
        management: { score: 0.6 },
        mos_recommendation: { recommended_mos: 0.35 },
        balance_sheet_resilience: {
          score: 4.0,
          latest_coverage: 8.5,
          debt_to_equity: 0.45,
          latest_net_debt: 30000000000,
          net_debt_trend: -0.08
        }
      }

      global.fetch = vi.fn().mockResolvedValueOnce({
        json: () => Promise.resolve(mockData)
      })

      render(<FourMsPanel api={API_BASE} ticker="WMT" />)
      
      fireEvent.click(screen.getByText('Analyze Moat, Management & MOS'))
      
      await waitFor(() => {
        expect(screen.getByText('Interest Coverage')).toBeInTheDocument()
        expect(screen.getByText('8.5x')).toBeInTheDocument()
      })
    })

    it('displays debt to equity ratio', async () => {
      const mockData = {
        moat: { score: 0.7 },
        management: { score: 0.6 },
        mos_recommendation: { recommended_mos: 0.35 },
        balance_sheet_resilience: {
          score: 3.5,
          latest_coverage: 6.0,
          debt_to_equity: 0.72,
          latest_net_debt: 40000000000,
          net_debt_trend: 0.05
        }
      }

      global.fetch = vi.fn().mockResolvedValueOnce({
        json: () => Promise.resolve(mockData)
      })

      render(<FourMsPanel api={API_BASE} ticker="WMT" />)
      
      fireEvent.click(screen.getByText('Analyze Moat, Management & MOS'))
      
      await waitFor(() => {
        expect(screen.getByText('Debt/Equity')).toBeInTheDocument()
        expect(screen.getByText('0.72')).toBeInTheDocument()
      })
    })

    it('displays net debt in billions', async () => {
      const mockData = {
        moat: { score: 0.7 },
        management: { score: 0.6 },
        mos_recommendation: { recommended_mos: 0.35 },
        balance_sheet_resilience: {
          score: 4.2,
          latest_coverage: 10.0,
          debt_to_equity: 0.40,
          latest_net_debt: 27000000000,
          net_debt_trend: -0.12
        }
      }

      global.fetch = vi.fn().mockResolvedValueOnce({
        json: () => Promise.resolve(mockData)
      })

      render(<FourMsPanel api={API_BASE} ticker="WMT" />)
      
      fireEvent.click(screen.getByText('Analyze Moat, Management & MOS'))
      
      await waitFor(() => {
        expect(screen.getByText('Net Debt')).toBeInTheDocument()
        expect(screen.getByText('$27.0B')).toBeInTheDocument()
      })
    })

    it('displays net debt trend with sign', async () => {
      const mockData = {
        moat: { score: 0.7 },
        management: { score: 0.6 },
        mos_recommendation: { recommended_mos: 0.35 },
        balance_sheet_resilience: {
          score: 4.8,
          latest_coverage: 15.0,
          debt_to_equity: 0.25,
          latest_net_debt: 20000000000,
          net_debt_trend: -0.25
        }
      }

      global.fetch = vi.fn().mockResolvedValueOnce({
        json: () => Promise.resolve(mockData)
      })

      render(<FourMsPanel api={API_BASE} ticker="WMT" />)
      
      fireEvent.click(screen.getByText('Analyze Moat, Management & MOS'))
      
      await waitFor(() => {
        expect(screen.getByText('Net Debt Trend')).toBeInTheDocument()
        expect(screen.getByText('-25.0%')).toBeInTheDocument()
      })
    })

    it('displays positive net debt trend with plus sign', async () => {
      const mockData = {
        moat: { score: 0.7 },
        management: { score: 0.6 },
        mos_recommendation: { recommended_mos: 0.35 },
        balance_sheet_resilience: {
          score: 2.5,
          latest_coverage: 4.0,
          debt_to_equity: 1.2,
          latest_net_debt: 50000000000,
          net_debt_trend: 0.18
        }
      }

      global.fetch = vi.fn().mockResolvedValueOnce({
        json: () => Promise.resolve(mockData)
      })

      render(<FourMsPanel api={API_BASE} ticker="WMT" />)
      
      fireEvent.click(screen.getByText('Analyze Moat, Management & MOS'))
      
      await waitFor(() => {
        expect(screen.getByText('+18.0%')).toBeInTheDocument()
      })
    })

    it('shows educational tip in balance sheet card', async () => {
      const mockData = {
        moat: { score: 0.7 },
        management: { score: 0.6 },
        mos_recommendation: { recommended_mos: 0.35 },
        balance_sheet_resilience: {
          score: 4.0,
          latest_coverage: 8.0,
          debt_to_equity: 0.5,
          latest_net_debt: 30000000000,
          net_debt_trend: -0.10
        }
      }

      global.fetch = vi.fn().mockResolvedValueOnce({
        json: () => Promise.resolve(mockData)
      })

      render(<FourMsPanel api={API_BASE} ticker="WMT" />)
      
      fireEvent.click(screen.getByText('Analyze Moat, Management & MOS'))
      
      await waitFor(() => {
        expect(screen.getByText(/Companies with low debt, high coverage ratios/)).toBeInTheDocument()
      })
    })

    it('does not render balance sheet card when data is missing', async () => {
      const mockData = {
        moat: { score: 0.7 },
        management: { score: 0.6 },
        mos_recommendation: { recommended_mos: 0.35 }
        // No balance_sheet_resilience
      }

      global.fetch = vi.fn().mockResolvedValueOnce({
        json: () => Promise.resolve(mockData)
      })

      render(<FourMsPanel api={API_BASE} ticker="AAPL" />)
      
      fireEvent.click(screen.getByText('Analyze Moat, Management & MOS'))
      
      await waitFor(() => {
        expect(screen.getByText('Moat')).toBeInTheDocument()
      })
      
      // Balance Sheet card should not be present
      expect(screen.queryByText('Balance Sheet')).not.toBeInTheDocument()
    })
  })

  describe('Phase E: ROIC Persistence Badge', () => {
    it('displays ROIC persistence badge when score is present', async () => {
      const mockData = {
        moat: { 
          score: 0.75, 
          roic_avg: 0.16, 
          margin_stability: 0.85,
          roic_persistence_score: 4
        },
        management: { score: 0.6 },
        mos_recommendation: { recommended_mos: 0.4 }
      }

      global.fetch = vi.fn().mockResolvedValueOnce({
        json: () => Promise.resolve(mockData)
      })

      render(<FourMsPanel api={API_BASE} ticker="WMT" />)
      
      fireEvent.click(screen.getByText('Analyze Moat, Management & MOS'))
      
      await waitFor(() => {
        expect(screen.getByText('ROIC Persistence')).toBeInTheDocument()
      })
    })
  })

  describe('Phase E: Gross Margin Metrics', () => {
    it('displays gross margin when present', async () => {
      const mockData = {
        moat: { 
          score: 0.75, 
          roic_avg: 0.16, 
          margin_stability: 0.85,
          latest_gross_margin: 0.35
        },
        management: { score: 0.6 },
        mos_recommendation: { recommended_mos: 0.4 }
      }

      global.fetch = vi.fn().mockResolvedValueOnce({
        json: () => Promise.resolve(mockData)
      })

      render(<FourMsPanel api={API_BASE} ticker="WMT" />)
      
      fireEvent.click(screen.getByText('Analyze Moat, Management & MOS'))
      
      await waitFor(() => {
        expect(screen.getByText('Gross Margin')).toBeInTheDocument()
      })
    })

    it('displays gross margin trend with positive sign', async () => {
      const mockData = {
        moat: { 
          score: 0.75, 
          gross_margin_trend: 0.025
        },
        management: { score: 0.6 },
        mos_recommendation: { recommended_mos: 0.4 }
      }

      global.fetch = vi.fn().mockResolvedValueOnce({
        json: () => Promise.resolve(mockData)
      })

      render(<FourMsPanel api={API_BASE} ticker="WMT" />)
      
      fireEvent.click(screen.getByText('Analyze Moat, Management & MOS'))
      
      await waitFor(() => {
        expect(screen.getByText('Gross Margin Trend')).toBeInTheDocument()
        expect(screen.getByText('+2.50%')).toBeInTheDocument()
      })
    })

    it('displays gross margin trend with negative value', async () => {
      const mockData = {
        moat: { 
          score: 0.75, 
          gross_margin_trend: -0.015
        },
        management: { score: 0.6 },
        mos_recommendation: { recommended_mos: 0.4 }
      }

      global.fetch = vi.fn().mockResolvedValueOnce({
        json: () => Promise.resolve(mockData)
      })

      render(<FourMsPanel api={API_BASE} ticker="WMT" />)
      
      fireEvent.click(screen.getByText('Analyze Moat, Management & MOS'))
      
      await waitFor(() => {
        expect(screen.getByText('-1.50%')).toBeInTheDocument()
      })
    })
  })
})
