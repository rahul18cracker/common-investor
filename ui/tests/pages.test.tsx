import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

// Mock ResizeObserver for Recharts
class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
global.ResizeObserver = ResizeObserver

// Mock the child components to isolate page tests
vi.mock('../components/BigFivePanel', () => ({
  default: ({ ticker }: { ticker: string }) => <div data-testid="big-five-panel">BigFivePanel: {ticker}</div>
}))

vi.mock('../components/CompanyDashboard', () => ({
  default: ({ ticker }: { ticker: string }) => <div data-testid="company-dashboard">CompanyDashboard: {ticker}</div>
}))

vi.mock('../components/ValuationPanel', () => ({
  default: ({ ticker }: { ticker: string }) => <div data-testid="valuation-panel">ValuationPanel: {ticker}</div>
}))

vi.mock('../components/FourMsPanel', () => ({
  default: ({ ticker }: { ticker: string }) => <div data-testid="fourms-panel">FourMsPanel: {ticker}</div>
}))

vi.mock('../components/AlertsPanel', () => ({
  default: ({ ticker }: { ticker: string }) => <div data-testid="alerts-panel">AlertsPanel: {ticker}</div>
}))

// Import components after mocking
import Home from '../app/page'
import RootLayout from '../app/layout'
import Company from '../app/company/[ticker]/page'

const API_BASE = 'http://localhost:8080'

describe('Home Page', () => {
  it('renders the home page with title', () => {
    render(<Home />)
    
    expect(screen.getByText('Common Investor')).toBeInTheDocument()
  })

  it('renders a link to example company', () => {
    render(<Home />)
    
    const link = screen.getByRole('link', { name: /MSFT/i })
    expect(link).toBeInTheDocument()
    expect(link).toHaveAttribute('href', '/company/MSFT')
  })

  it('renders instruction text', () => {
    render(<Home />)
    
    expect(screen.getByText(/Open a company page/)).toBeInTheDocument()
  })
})

describe('RootLayout', () => {
  it('renders children within html and body tags', () => {
    render(
      <RootLayout>
        <div data-testid="child">Test Child</div>
      </RootLayout>
    )
    
    expect(screen.getByTestId('child')).toBeInTheDocument()
    expect(screen.getByText('Test Child')).toBeInTheDocument()
  })

  it('sets lang attribute to en', () => {
    const { container } = render(
      <RootLayout>
        <div>Content</div>
      </RootLayout>
    )
    
    const html = container.querySelector('html')
    expect(html).toHaveAttribute('lang', 'en')
  })
})

describe('Company Page', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    // Mock window.alert
    vi.spyOn(window, 'alert').mockImplementation(() => {})
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders the company page with ticker', async () => {
    global.fetch = vi.fn().mockResolvedValueOnce({
      status: 200,
      json: () => Promise.resolve({ name: 'Apple Inc.' })
    })

    render(<Company params={{ ticker: 'AAPL' }} />)
    
    await waitFor(() => {
      expect(screen.getByText('AAPL')).toBeInTheDocument()
    })
  })

  it('displays company name when available', async () => {
    global.fetch = vi.fn().mockResolvedValueOnce({
      status: 200,
      json: () => Promise.resolve({ name: 'Microsoft Corporation' })
    })

    render(<Company params={{ ticker: 'MSFT' }} />)
    
    await waitFor(() => {
      expect(screen.getByText('Microsoft Corporation')).toBeInTheDocument()
    })
  })

  it('shows loading state initially', () => {
    global.fetch = vi.fn().mockImplementation(() => 
      new Promise(resolve => setTimeout(() => resolve({
        status: 200,
        json: () => Promise.resolve({ name: 'Test' })
      }), 100))
    )

    render(<Company params={{ ticker: 'AAPL' }} />)
    
    expect(screen.getByText('Loading company data...')).toBeInTheDocument()
  })

  it('handles 404 response', async () => {
    global.fetch = vi.fn().mockResolvedValueOnce({
      status: 404,
      json: () => Promise.resolve(null)
    })

    render(<Company params={{ ticker: 'INVALID' }} />)
    
    await waitFor(() => {
      expect(screen.getByText(/No data available for INVALID/)).toBeInTheDocument()
    })
  })

  it('handles fetch error', async () => {
    global.fetch = vi.fn().mockRejectedValueOnce(new Error('Network error'))

    render(<Company params={{ ticker: 'AAPL' }} />)
    
    await waitFor(() => {
      expect(screen.getByText(/Error:/)).toBeInTheDocument()
    })
  })

  it('renders action buttons', async () => {
    global.fetch = vi.fn().mockResolvedValueOnce({
      status: 200,
      json: () => Promise.resolve({ name: 'Apple Inc.' })
    })

    render(<Company params={{ ticker: 'AAPL' }} />)
    
    await waitFor(() => {
      expect(screen.getByText('Ingest SEC Data')).toBeInTheDocument()
      expect(screen.getByText('Reload')).toBeInTheDocument()
      expect(screen.getByText('Export CSV')).toBeInTheDocument()
    })
  })

  it('calls ingest API on button click', async () => {
    global.fetch = vi.fn()
      .mockResolvedValueOnce({
        status: 200,
        json: () => Promise.resolve({ name: 'Apple Inc.' })
      })
      .mockResolvedValueOnce({
        status: 200,
        json: () => Promise.resolve({ status: 'queued' })
      })

    render(<Company params={{ ticker: 'AAPL' }} />)
    
    await waitFor(() => {
      expect(screen.getByText('Ingest SEC Data')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByText('Ingest SEC Data'))
    
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        `${API_BASE}/api/v1/company/AAPL/ingest`,
        { method: 'POST' }
      )
    })
  })

  it('shows ingesting state during ingest', async () => {
    global.fetch = vi.fn()
      .mockResolvedValueOnce({
        status: 200,
        json: () => Promise.resolve({ name: 'Apple Inc.' })
      })
      .mockImplementationOnce(() => 
        new Promise(resolve => setTimeout(() => resolve({
          status: 200,
          json: () => Promise.resolve({ status: 'queued' })
        }), 100))
      )

    render(<Company params={{ ticker: 'AAPL' }} />)
    
    await waitFor(() => {
      expect(screen.getByText('Ingest SEC Data')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByText('Ingest SEC Data'))
    
    expect(screen.getByText('Ingesting...')).toBeInTheDocument()
  })

  it('reloads data on reload button click', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      status: 200,
      json: () => Promise.resolve({ name: 'Apple Inc.' })
    })

    render(<Company params={{ ticker: 'AAPL' }} />)
    
    await waitFor(() => {
      expect(screen.getByText('Reload')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByText('Reload'))
    
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledTimes(2)
    })
  })

  it('renders all child panels', async () => {
    global.fetch = vi.fn().mockResolvedValueOnce({
      status: 200,
      json: () => Promise.resolve({ name: 'Apple Inc.' })
    })

    render(<Company params={{ ticker: 'AAPL' }} />)
    
    await waitFor(() => {
      expect(screen.getByTestId('big-five-panel')).toBeInTheDocument()
      expect(screen.getByTestId('fourms-panel')).toBeInTheDocument()
      expect(screen.getByTestId('valuation-panel')).toBeInTheDocument()
      expect(screen.getByTestId('company-dashboard')).toBeInTheDocument()
      expect(screen.getByTestId('alerts-panel')).toBeInTheDocument()
    })
  })

  it('passes ticker to child panels', async () => {
    global.fetch = vi.fn().mockResolvedValueOnce({
      status: 200,
      json: () => Promise.resolve({ name: 'Apple Inc.' })
    })

    render(<Company params={{ ticker: 'GOOGL' }} />)
    
    await waitFor(() => {
      expect(screen.getByText('BigFivePanel: GOOGL')).toBeInTheDocument()
      expect(screen.getByText('FourMsPanel: GOOGL')).toBeInTheDocument()
      expect(screen.getByText('ValuationPanel: GOOGL')).toBeInTheDocument()
      expect(screen.getByText('CompanyDashboard: GOOGL')).toBeInTheDocument()
      expect(screen.getByText('AlertsPanel: GOOGL')).toBeInTheDocument()
    })
  })

  it('renders export CSV link with correct URL', async () => {
    global.fetch = vi.fn().mockResolvedValueOnce({
      status: 200,
      json: () => Promise.resolve({ name: 'Apple Inc.' })
    })

    render(<Company params={{ ticker: 'AAPL' }} />)
    
    await waitFor(() => {
      const exportLink = screen.getByText('Export CSV')
      expect(exportLink).toHaveAttribute('href', `${API_BASE}/api/v1/company/AAPL/export/metrics.csv`)
      expect(exportLink).toHaveAttribute('target', '_blank')
    })
  })

  it('shows raw data in collapsible details', async () => {
    const mockSummary = { name: 'Apple Inc.', cik: '0000320193' }
    global.fetch = vi.fn().mockResolvedValueOnce({
      status: 200,
      json: () => Promise.resolve(mockSummary)
    })

    render(<Company params={{ ticker: 'AAPL' }} />)
    
    await waitFor(() => {
      expect(screen.getByText('View Raw Company Data')).toBeInTheDocument()
    })
  })

  it('displays Rule #1 description', async () => {
    global.fetch = vi.fn().mockResolvedValueOnce({
      status: 200,
      json: () => Promise.resolve({ name: 'Apple Inc.' })
    })

    render(<Company params={{ ticker: 'AAPL' }} />)
    
    await waitFor(() => {
      expect(screen.getByText(/Rule #1 Investing Analysis/)).toBeInTheDocument()
    })
  })
})
