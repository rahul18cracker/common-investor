import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'

// Mock fetch globally
const mockFetch = vi.fn()
global.fetch = mockFetch

// Import after mocking
import ValuationPanel from '../components/ValuationPanel'

describe('ValuationPanel', () => {
  beforeEach(() => {
    mockFetch.mockReset()
  })

  describe('Initial Render', () => {
    it('renders section title', () => {
      render(<ValuationPanel api="http://localhost:8000" ticker="MSFT" />)
      expect(screen.getByText('Valuation Calculator')).toBeInTheDocument()
    })

    it('renders description text', () => {
      render(<ValuationPanel api="http://localhost:8000" ticker="MSFT" />)
      expect(screen.getByText(/Calculate the intrinsic value/)).toBeInTheDocument()
    })

    it('renders Margin of Safety slider', () => {
      render(<ValuationPanel api="http://localhost:8000" ticker="MSFT" />)
      expect(screen.getByText('Margin of Safety')).toBeInTheDocument()
    })

    it('renders Growth Rate slider', () => {
      render(<ValuationPanel api="http://localhost:8000" ticker="MSFT" />)
      expect(screen.getByText('Growth Rate (g)')).toBeInTheDocument()
    })

    it('renders Calculate Valuation button', () => {
      render(<ValuationPanel api="http://localhost:8000" ticker="MSFT" />)
      expect(screen.getByText('Calculate Valuation')).toBeInTheDocument()
    })

    it('renders Export JSON link', () => {
      render(<ValuationPanel api="http://localhost:8000" ticker="MSFT" />)
      expect(screen.getByText('Export JSON')).toBeInTheDocument()
    })

    it('renders educational content when no valuation', () => {
      render(<ValuationPanel api="http://localhost:8000" ticker="MSFT" />)
      expect(screen.getByText('Understanding Rule #1 Valuation')).toBeInTheDocument()
    })

    it('renders Advanced Settings toggle', () => {
      render(<ValuationPanel api="http://localhost:8000" ticker="MSFT" />)
      expect(screen.getByText(/Advanced Settings/)).toBeInTheDocument()
    })
  })

  describe('Advanced Settings', () => {
    it('shows advanced settings when toggled', () => {
      render(<ValuationPanel api="http://localhost:8000" ticker="MSFT" />)
      
      const advancedButton = screen.getByText(/Advanced Settings/)
      fireEvent.click(advancedButton)
      
      expect(screen.getByText('PE Cap')).toBeInTheDocument()
      expect(screen.getByText('Discount Rate')).toBeInTheDocument()
    })

    it('hides advanced settings when toggled again', () => {
      render(<ValuationPanel api="http://localhost:8000" ticker="MSFT" />)
      
      const advancedButton = screen.getByText(/Advanced Settings/)
      fireEvent.click(advancedButton)
      fireEvent.click(advancedButton)
      
      expect(screen.queryByText('PE Cap')).not.toBeInTheDocument()
    })
  })

  describe('Valuation Calculation', () => {
    const mockValuation = {
      sticker: 150.50,
      mos_price: 75.25,
      ten_cap_price: 120.00,
      payback_years: 6.5,
      eps0: 5.25,
      g: 0.10,
      future_eps: 13.62,
      pe_used: 20,
      future_price: 272.40,
      owner_earnings: 50000000000,
    }

    it('calls API with correct parameters on calculate', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockValuation),
      })
      
      render(<ValuationPanel api="http://localhost:8000" ticker="AAPL" />)
      
      const calculateButton = screen.getByText('Calculate Valuation')
      fireEvent.click(calculateButton)
      
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          'http://localhost:8000/api/v1/company/AAPL/valuation',
          expect.objectContaining({
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
          })
        )
      })
    })

    it('displays loading state during calculation', async () => {
      mockFetch.mockImplementation(() => new Promise(() => {})) // Never resolves
      
      render(<ValuationPanel api="http://localhost:8000" ticker="MSFT" />)
      
      const calculateButton = screen.getByText('Calculate Valuation')
      fireEvent.click(calculateButton)
      
      expect(screen.getByText('Calculating...')).toBeInTheDocument()
    })

    it('displays valuation results on success', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockValuation),
      })
      
      render(<ValuationPanel api="http://localhost:8000" ticker="MSFT" />)
      
      const calculateButton = screen.getByText('Calculate Valuation')
      fireEvent.click(calculateButton)
      
      await waitFor(() => {
        expect(screen.getByText('Sticker Price')).toBeInTheDocument()
        expect(screen.getByText('MOS Price')).toBeInTheDocument()
        expect(screen.getByText('Ten Cap Price')).toBeInTheDocument()
        expect(screen.getByText('Payback Time')).toBeInTheDocument()
      })
    })

    it('displays formatted sticker price', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockValuation),
      })
      
      render(<ValuationPanel api="http://localhost:8000" ticker="MSFT" />)
      
      const calculateButton = screen.getByText('Calculate Valuation')
      fireEvent.click(calculateButton)
      
      await waitFor(() => {
        expect(screen.getByText('$150.50')).toBeInTheDocument()
      })
    })

    it('displays formatted MOS price', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockValuation),
      })
      
      render(<ValuationPanel api="http://localhost:8000" ticker="MSFT" />)
      
      const calculateButton = screen.getByText('Calculate Valuation')
      fireEvent.click(calculateButton)
      
      await waitFor(() => {
        expect(screen.getByText('$75.25')).toBeInTheDocument()
      })
    })

    it('hides educational content after calculation', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockValuation),
      })
      
      render(<ValuationPanel api="http://localhost:8000" ticker="MSFT" />)
      
      const calculateButton = screen.getByText('Calculate Valuation')
      fireEvent.click(calculateButton)
      
      await waitFor(() => {
        expect(screen.queryByText('Understanding Rule #1 Valuation')).not.toBeInTheDocument()
      })
    })

    it('displays calculation details section', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockValuation),
      })
      
      render(<ValuationPanel api="http://localhost:8000" ticker="MSFT" />)
      
      const calculateButton = screen.getByText('Calculate Valuation')
      fireEvent.click(calculateButton)
      
      await waitFor(() => {
        expect(screen.getByText('View Calculation Details')).toBeInTheDocument()
      })
    })

    it('displays raw JSON section', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockValuation),
      })
      
      render(<ValuationPanel api="http://localhost:8000" ticker="MSFT" />)
      
      const calculateButton = screen.getByText('Calculate Valuation')
      fireEvent.click(calculateButton)
      
      await waitFor(() => {
        expect(screen.getByText('View Raw JSON Response')).toBeInTheDocument()
      })
    })
  })

  describe('Export URL', () => {
    it('generates correct export URL with default MOS', () => {
      render(<ValuationPanel api="http://localhost:8000" ticker="MSFT" />)
      
      const exportLink = screen.getByText('Export JSON').closest('a')
      expect(exportLink).toHaveAttribute(
        'href',
        'http://localhost:8000/api/v1/company/MSFT/export/valuation.json?mos_pct=0.5'
      )
    })

    it('has correct link attributes for security', () => {
      render(<ValuationPanel api="http://localhost:8000" ticker="MSFT" />)
      
      const exportLink = screen.getByText('Export JSON').closest('a')
      expect(exportLink).toHaveAttribute('target', '_blank')
      expect(exportLink).toHaveAttribute('rel', 'noreferrer')
    })
  })

  describe('Null Value Handling', () => {
    it('displays N/A for null sticker price', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ sticker: null, mos_price: null }),
      })
      
      render(<ValuationPanel api="http://localhost:8000" ticker="MSFT" />)
      
      const calculateButton = screen.getByText('Calculate Valuation')
      fireEvent.click(calculateButton)
      
      await waitFor(() => {
        const naElements = screen.getAllByText('N/A')
        expect(naElements.length).toBeGreaterThan(0)
      })
    })
  })
})

// Unit tests for SliderInput component behavior
describe('SliderInput Component', () => {
  it('displays initial value correctly', () => {
    render(<ValuationPanel api="http://localhost:8000" ticker="MSFT" />)
    expect(screen.getByText('50%')).toBeInTheDocument() // Default MOS
    expect(screen.getByText('10%')).toBeInTheDocument() // Default growth
  })
})

// Unit tests for PriceCard formatting
describe('PriceCard Formatting', () => {
  it('formats price with two decimal places', async () => {
    const mockFetch = vi.fn().mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ sticker: 123.456 }),
    })
    global.fetch = mockFetch
    
    render(<ValuationPanel api="http://localhost:8000" ticker="MSFT" />)
    
    const calculateButton = screen.getByText('Calculate Valuation')
    fireEvent.click(calculateButton)
    
    await waitFor(() => {
      expect(screen.getByText('$123.46')).toBeInTheDocument()
    })
  })
})
