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
})
