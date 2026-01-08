import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'

const mockFetch = vi.fn()
global.fetch = mockFetch

import IncomeStatementPanel from '../components/IncomeStatementPanel'

describe('IncomeStatementPanel', () => {
  beforeEach(() => {
    mockFetch.mockReset()
  })

  describe('Loading State', () => {
    it('shows loading message initially', () => {
      mockFetch.mockImplementation(() => new Promise(() => {}))
      render(<IncomeStatementPanel api="http://localhost:8000" ticker="MSFT" />)
      expect(screen.getByText('Loading...')).toBeInTheDocument()
    })

    it('displays section title while loading', () => {
      mockFetch.mockImplementation(() => new Promise(() => {}))
      render(<IncomeStatementPanel api="http://localhost:8000" ticker="MSFT" />)
      expect(screen.getByText('Income Statement Breakdown')).toBeInTheDocument()
    })
  })

  describe('Error State', () => {
    it('shows error message on fetch failure', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'))
      render(<IncomeStatementPanel api="http://localhost:8000" ticker="MSFT" />)
      
      await waitFor(() => {
        expect(screen.getByText(/Network error/)).toBeInTheDocument()
      })
    })

    it('shows message when no data available', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ latest_is: null }),
      })
      render(<IncomeStatementPanel api="http://localhost:8000" ticker="MSFT" />)
      
      await waitFor(() => {
        expect(screen.getByText(/No income statement data available/)).toBeInTheDocument()
      })
    })
  })

  describe('Success State', () => {
    const mockCompanyData = {
      company: { id: 1, cik: '0000789019', ticker: 'MSFT', name: 'Microsoft' },
      latest_is: {
        fy: 2023,
        revenue: 211915000000,
        cogs: 65863000000,
        gross_profit: 146052000000,
        sga: 22759000000,
        rnd: 27195000000,
        depreciation: 13861000000,
        ebit: 88523000000,
        interest_expense: 1968000000,
        taxes: 16950000000,
        net_income: 72361000000,
        eps_diluted: 9.72,
        shares_diluted: 7446000000,
        gross_margin: 0.689,
        operating_margin: 0.418,
      },
    }

    it('renders profitability margins section', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockCompanyData),
      })
      render(<IncomeStatementPanel api="http://localhost:8000" ticker="MSFT" />)
      
      await waitFor(() => {
        expect(screen.getByText('Profitability Margins')).toBeInTheDocument()
      })
    })

    it('displays gross margin correctly', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockCompanyData),
      })
      render(<IncomeStatementPanel api="http://localhost:8000" ticker="MSFT" />)
      
      await waitFor(() => {
        expect(screen.getByText('Gross Margin')).toBeInTheDocument()
        expect(screen.getByText('68.9%')).toBeInTheDocument()
      })
    })

    it('displays operating margin correctly', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockCompanyData),
      })
      render(<IncomeStatementPanel api="http://localhost:8000" ticker="MSFT" />)
      
      await waitFor(() => {
        expect(screen.getByText('Operating Margin')).toBeInTheDocument()
        expect(screen.getByText('41.8%')).toBeInTheDocument()
      })
    })

    it('renders income statement flow section', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockCompanyData),
      })
      render(<IncomeStatementPanel api="http://localhost:8000" ticker="MSFT" />)
      
      await waitFor(() => {
        expect(screen.getByText('Income Statement Flow')).toBeInTheDocument()
      })
    })

    it('displays revenue in the waterfall', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockCompanyData),
      })
      render(<IncomeStatementPanel api="http://localhost:8000" ticker="MSFT" />)
      
      await waitFor(() => {
        expect(screen.getByText('Revenue')).toBeInTheDocument()
        expect(screen.getByText('$211.9B')).toBeInTheDocument()
      })
    })

    it('displays gross profit in the waterfall', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockCompanyData),
      })
      render(<IncomeStatementPanel api="http://localhost:8000" ticker="MSFT" />)
      
      await waitFor(() => {
        expect(screen.getByText('= Gross Profit')).toBeInTheDocument()
        expect(screen.getByText('$146.1B')).toBeInTheDocument()
      })
    })

    it('displays EBIT in the waterfall', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockCompanyData),
      })
      render(<IncomeStatementPanel api="http://localhost:8000" ticker="MSFT" />)
      
      await waitFor(() => {
        expect(screen.getByText('= Operating Income (EBIT)')).toBeInTheDocument()
        expect(screen.getByText('$88.5B')).toBeInTheDocument()
      })
    })

    it('displays net income in the waterfall', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockCompanyData),
      })
      render(<IncomeStatementPanel api="http://localhost:8000" ticker="MSFT" />)
      
      await waitFor(() => {
        expect(screen.getByText('= Net Income')).toBeInTheDocument()
        expect(screen.getByText('$72.4B')).toBeInTheDocument()
      })
    })

    it('displays cost items in the waterfall', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockCompanyData),
      })
      render(<IncomeStatementPanel api="http://localhost:8000" ticker="MSFT" />)
      
      await waitFor(() => {
        expect(screen.getByText(/Cost of Revenue/)).toBeInTheDocument()
        expect(screen.getByText(/SG&A Expenses/)).toBeInTheDocument()
        expect(screen.getByText(/R&D Expenses/)).toBeInTheDocument()
        expect(screen.getByText(/Depreciation/)).toBeInTheDocument()
      })
    })

    it('displays fiscal year in subtitle', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockCompanyData),
      })
      render(<IncomeStatementPanel api="http://localhost:8000" ticker="MSFT" />)
      
      await waitFor(() => {
        expect(screen.getByText(/FY2023/)).toBeInTheDocument()
      })
    })

    it('displays educational note about margins', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockCompanyData),
      })
      render(<IncomeStatementPanel api="http://localhost:8000" ticker="MSFT" />)
      
      await waitFor(() => {
        expect(screen.getByText(/Why margins matter/)).toBeInTheDocument()
      })
    })
  })

  describe('API Integration', () => {
    it('calls correct API endpoint', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ latest_is: null }),
      })
      render(<IncomeStatementPanel api="http://localhost:8000" ticker="AAPL" />)
      
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith('http://localhost:8000/api/v1/company/AAPL')
      })
    })
  })
})
