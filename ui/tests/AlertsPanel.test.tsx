import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'

// Mock fetch globally
const mockFetch = vi.fn()
global.fetch = mockFetch

// Mock window.prompt
const mockPrompt = vi.fn()
global.prompt = mockPrompt

// Import after mocking
import AlertsPanel from '../components/AlertsPanel'

describe('AlertsPanel', () => {
  beforeEach(() => {
    mockFetch.mockReset()
    mockPrompt.mockReset()
  })

  describe('Initial Render', () => {
    it('renders section title', async () => {
      mockFetch.mockResolvedValueOnce({
        status: 200,
        json: () => Promise.resolve([]),
      })
      
      render(<AlertsPanel api="http://localhost:8000" ticker="MSFT" />)
      expect(screen.getByText('Alerts')).toBeInTheDocument()
    })

    it('renders Add Price < MOS button', async () => {
      mockFetch.mockResolvedValueOnce({
        status: 200,
        json: () => Promise.resolve([]),
      })
      
      render(<AlertsPanel api="http://localhost:8000" ticker="MSFT" />)
      expect(screen.getByText('Add: Price < MOS')).toBeInTheDocument()
    })

    it('renders Add Price < Threshold button', async () => {
      mockFetch.mockResolvedValueOnce({
        status: 200,
        json: () => Promise.resolve([]),
      })
      
      render(<AlertsPanel api="http://localhost:8000" ticker="MSFT" />)
      expect(screen.getByText('Add: Price < Threshold')).toBeInTheDocument()
    })

    it('renders table headers', async () => {
      mockFetch.mockResolvedValueOnce({
        status: 200,
        json: () => Promise.resolve([]),
      })
      
      render(<AlertsPanel api="http://localhost:8000" ticker="MSFT" />)
      
      expect(screen.getByText('ID')).toBeInTheDocument()
      expect(screen.getByText('Rule')).toBeInTheDocument()
      expect(screen.getByText('Threshold')).toBeInTheDocument()
      expect(screen.getByText('Enabled')).toBeInTheDocument()
      expect(screen.getByText('Actions')).toBeInTheDocument()
    })

    it('fetches alerts on mount', async () => {
      mockFetch.mockResolvedValueOnce({
        status: 200,
        json: () => Promise.resolve([]),
      })
      
      render(<AlertsPanel api="http://localhost:8000" ticker="AAPL" />)
      
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith('http://localhost:8000/api/v1/company/AAPL/alerts')
      })
    })
  })

  describe('Displaying Alerts', () => {
    const mockAlerts = [
      { id: 1, rule_type: 'price_below_mos', threshold: null, enabled: true },
      { id: 2, rule_type: 'price_below_threshold', threshold: 150.50, enabled: false },
    ]

    it('displays alert rows', async () => {
      mockFetch.mockResolvedValueOnce({
        status: 200,
        json: () => Promise.resolve(mockAlerts),
      })
      
      render(<AlertsPanel api="http://localhost:8000" ticker="MSFT" />)
      
      await waitFor(() => {
        expect(screen.getByText('price_below_mos')).toBeInTheDocument()
        expect(screen.getByText('price_below_threshold')).toBeInTheDocument()
      })
    })

    it('displays alert IDs', async () => {
      mockFetch.mockResolvedValueOnce({
        status: 200,
        json: () => Promise.resolve(mockAlerts),
      })
      
      render(<AlertsPanel api="http://localhost:8000" ticker="MSFT" />)
      
      await waitFor(() => {
        expect(screen.getByText('1')).toBeInTheDocument()
        expect(screen.getByText('2')).toBeInTheDocument()
      })
    })

    it('displays threshold or dash for null', async () => {
      mockFetch.mockResolvedValueOnce({
        status: 200,
        json: () => Promise.resolve(mockAlerts),
      })
      
      render(<AlertsPanel api="http://localhost:8000" ticker="MSFT" />)
      
      await waitFor(() => {
        expect(screen.getByText('—')).toBeInTheDocument()
        expect(screen.getByText('150.5')).toBeInTheDocument()
      })
    })

    it('displays enabled status', async () => {
      mockFetch.mockResolvedValueOnce({
        status: 200,
        json: () => Promise.resolve(mockAlerts),
      })
      
      render(<AlertsPanel api="http://localhost:8000" ticker="MSFT" />)
      
      await waitFor(() => {
        expect(screen.getByText('true')).toBeInTheDocument()
        expect(screen.getByText('false')).toBeInTheDocument()
      })
    })

    it('displays Disable button for enabled alerts', async () => {
      mockFetch.mockResolvedValueOnce({
        status: 200,
        json: () => Promise.resolve([{ id: 1, rule_type: 'test', enabled: true }]),
      })
      
      render(<AlertsPanel api="http://localhost:8000" ticker="MSFT" />)
      
      await waitFor(() => {
        expect(screen.getByText('Disable')).toBeInTheDocument()
      })
    })

    it('displays Enable button for disabled alerts', async () => {
      mockFetch.mockResolvedValueOnce({
        status: 200,
        json: () => Promise.resolve([{ id: 1, rule_type: 'test', enabled: false }]),
      })
      
      render(<AlertsPanel api="http://localhost:8000" ticker="MSFT" />)
      
      await waitFor(() => {
        expect(screen.getByText('Enable')).toBeInTheDocument()
      })
    })

    it('displays Delete button for each alert', async () => {
      mockFetch.mockResolvedValueOnce({
        status: 200,
        json: () => Promise.resolve([{ id: 1, rule_type: 'test', enabled: true }]),
      })
      
      render(<AlertsPanel api="http://localhost:8000" ticker="MSFT" />)
      
      await waitFor(() => {
        expect(screen.getByText('Delete')).toBeInTheDocument()
      })
    })
  })

  describe('Creating Alerts', () => {
    it('creates price_below_mos alert on button click', async () => {
      mockFetch
        .mockResolvedValueOnce({ status: 200, json: () => Promise.resolve([]) }) // Initial load
        .mockResolvedValueOnce({ ok: true }) // POST create
        .mockResolvedValueOnce({ status: 200, json: () => Promise.resolve([]) }) // Reload
      
      render(<AlertsPanel api="http://localhost:8000" ticker="MSFT" />)
      
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledTimes(1)
      })
      
      const addButton = screen.getByText('Add: Price < MOS')
      fireEvent.click(addButton)
      
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          'http://localhost:8000/api/v1/company/MSFT/alerts',
          expect.objectContaining({
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ rule_type: 'price_below_mos' }),
          })
        )
      })
    })

    it('creates price_below_threshold alert with user-provided threshold', async () => {
      mockFetch
        .mockResolvedValueOnce({ status: 200, json: () => Promise.resolve([]) })
        .mockResolvedValueOnce({ ok: true })
        .mockResolvedValueOnce({ status: 200, json: () => Promise.resolve([]) })
      
      mockPrompt.mockReturnValueOnce('100.50')
      
      render(<AlertsPanel api="http://localhost:8000" ticker="MSFT" />)
      
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledTimes(1)
      })
      
      const addButton = screen.getByText('Add: Price < Threshold')
      fireEvent.click(addButton)
      
      await waitFor(() => {
        expect(mockPrompt).toHaveBeenCalledWith('Threshold price?')
        expect(mockFetch).toHaveBeenCalledWith(
          'http://localhost:8000/api/v1/company/MSFT/alerts',
          expect.objectContaining({
            method: 'POST',
            body: JSON.stringify({ rule_type: 'price_below_threshold', threshold: 100.50 }),
          })
        )
      })
    })

    it('does not create alert if user cancels prompt', async () => {
      mockFetch.mockResolvedValueOnce({ status: 200, json: () => Promise.resolve([]) })
      mockPrompt.mockReturnValueOnce(null)
      
      render(<AlertsPanel api="http://localhost:8000" ticker="MSFT" />)
      
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledTimes(1)
      })
      
      const addButton = screen.getByText('Add: Price < Threshold')
      fireEvent.click(addButton)
      
      // Should not make additional fetch calls
      expect(mockFetch).toHaveBeenCalledTimes(1)
    })
  })

  describe('Toggling Alerts', () => {
    it('disables an enabled alert', async () => {
      mockFetch
        .mockResolvedValueOnce({ 
          status: 200, 
          json: () => Promise.resolve([{ id: 1, rule_type: 'test', enabled: true }]) 
        })
        .mockResolvedValueOnce({ ok: true }) // PATCH
        .mockResolvedValueOnce({ status: 200, json: () => Promise.resolve([]) }) // Reload
      
      render(<AlertsPanel api="http://localhost:8000" ticker="MSFT" />)
      
      await waitFor(() => {
        expect(screen.getByText('Disable')).toBeInTheDocument()
      })
      
      const disableButton = screen.getByText('Disable')
      fireEvent.click(disableButton)
      
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          'http://localhost:8000/api/v1/alerts/1',
          expect.objectContaining({
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ enabled: false }),
          })
        )
      })
    })

    it('enables a disabled alert', async () => {
      mockFetch
        .mockResolvedValueOnce({ 
          status: 200, 
          json: () => Promise.resolve([{ id: 2, rule_type: 'test', enabled: false }]) 
        })
        .mockResolvedValueOnce({ ok: true })
        .mockResolvedValueOnce({ status: 200, json: () => Promise.resolve([]) })
      
      render(<AlertsPanel api="http://localhost:8000" ticker="MSFT" />)
      
      await waitFor(() => {
        expect(screen.getByText('Enable')).toBeInTheDocument()
      })
      
      const enableButton = screen.getByText('Enable')
      fireEvent.click(enableButton)
      
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          'http://localhost:8000/api/v1/alerts/2',
          expect.objectContaining({
            method: 'PATCH',
            body: JSON.stringify({ enabled: true }),
          })
        )
      })
    })
  })

  describe('Deleting Alerts', () => {
    it('deletes an alert', async () => {
      mockFetch
        .mockResolvedValueOnce({ 
          status: 200, 
          json: () => Promise.resolve([{ id: 5, rule_type: 'test', enabled: true }]) 
        })
        .mockResolvedValueOnce({ ok: true }) // DELETE
        .mockResolvedValueOnce({ status: 200, json: () => Promise.resolve([]) }) // Reload
      
      render(<AlertsPanel api="http://localhost:8000" ticker="MSFT" />)
      
      await waitFor(() => {
        expect(screen.getByText('Delete')).toBeInTheDocument()
      })
      
      const deleteButton = screen.getByText('Delete')
      fireEvent.click(deleteButton)
      
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          'http://localhost:8000/api/v1/alerts/5',
          expect.objectContaining({
            method: 'DELETE',
          })
        )
      })
    })
  })

  describe('Error Handling', () => {
    it('handles non-200 response gracefully', async () => {
      mockFetch.mockResolvedValueOnce({
        status: 500,
      })

      render(<AlertsPanel api="http://localhost:8000" ticker="MSFT" />)

      // Should not crash, alerts should be empty
      await waitFor(() => {
        expect(screen.getByText('Alerts')).toBeInTheDocument()
      })
    })

    it('handles fetch rejection on initial load', async () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
      mockFetch.mockRejectedValueOnce(new Error('Network error'))

      render(<AlertsPanel api="http://localhost:8000" ticker="MSFT" />)

      await waitFor(() => {
        expect(consoleSpy).toHaveBeenCalledWith('Failed to load alerts:', 'Network error')
      })
      consoleSpy.mockRestore()
    })

    it('handles fetch rejection on create MOS alert', async () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
      mockFetch
        .mockResolvedValueOnce({ status: 200, json: () => Promise.resolve([]) })
        .mockRejectedValueOnce(new Error('Create failed'))

      render(<AlertsPanel api="http://localhost:8000" ticker="MSFT" />)
      await waitFor(() => { expect(mockFetch).toHaveBeenCalledTimes(1) })

      fireEvent.click(screen.getByText('Add: Price < MOS'))

      await waitFor(() => {
        expect(consoleSpy).toHaveBeenCalledWith('Failed to create alert:', 'Create failed')
      })
      consoleSpy.mockRestore()
    })

    it('handles fetch rejection on create threshold alert', async () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
      mockFetch
        .mockResolvedValueOnce({ status: 200, json: () => Promise.resolve([]) })
        .mockRejectedValueOnce(new Error('Create failed'))
      mockPrompt.mockReturnValueOnce('100')

      render(<AlertsPanel api="http://localhost:8000" ticker="MSFT" />)
      await waitFor(() => { expect(mockFetch).toHaveBeenCalledTimes(1) })

      fireEvent.click(screen.getByText('Add: Price < Threshold'))

      await waitFor(() => {
        expect(consoleSpy).toHaveBeenCalledWith('Failed to create alert:', 'Create failed')
      })
      consoleSpy.mockRestore()
    })

    it('handles fetch rejection on toggle alert', async () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
      mockFetch
        .mockResolvedValueOnce({ status: 200, json: () => Promise.resolve([{ id: 1, rule_type: 'test', threshold: null, enabled: true }]) })
        .mockRejectedValueOnce(new Error('Toggle failed'))

      render(<AlertsPanel api="http://localhost:8000" ticker="MSFT" />)
      await waitFor(() => { expect(screen.getByText('Disable')).toBeInTheDocument() })

      fireEvent.click(screen.getByText('Disable'))

      await waitFor(() => {
        expect(consoleSpy).toHaveBeenCalledWith('Failed to toggle alert:', 'Toggle failed')
      })
      consoleSpy.mockRestore()
    })

    it('handles fetch rejection on delete alert', async () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
      mockFetch
        .mockResolvedValueOnce({ status: 200, json: () => Promise.resolve([{ id: 1, rule_type: 'test', threshold: null, enabled: true }]) })
        .mockRejectedValueOnce(new Error('Delete failed'))

      render(<AlertsPanel api="http://localhost:8000" ticker="MSFT" />)
      await waitFor(() => { expect(screen.getByText('Delete')).toBeInTheDocument() })

      fireEvent.click(screen.getByText('Delete'))

      await waitFor(() => {
        expect(consoleSpy).toHaveBeenCalledWith('Failed to delete alert:', 'Delete failed')
      })
      consoleSpy.mockRestore()
    })
  })

  describe('Ticker Change', () => {
    it('refetches alerts when ticker changes', async () => {
      mockFetch
        .mockResolvedValueOnce({ status: 200, json: () => Promise.resolve([]) })
        .mockResolvedValueOnce({ status: 200, json: () => Promise.resolve([]) })
      
      const { rerender } = render(<AlertsPanel api="http://localhost:8000" ticker="MSFT" />)
      
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith('http://localhost:8000/api/v1/company/MSFT/alerts')
      })
      
      rerender(<AlertsPanel api="http://localhost:8000" ticker="AAPL" />)
      
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith('http://localhost:8000/api/v1/company/AAPL/alerts')
      })
    })
  })
})
