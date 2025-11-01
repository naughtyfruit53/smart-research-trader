import { render, screen } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { SignalsTable } from '../SignalsTable'
import { SignalItem } from '@/lib/api'
import { describe, it, expect, vi } from 'vitest'

describe('SignalsTable', () => {
  const mockSignals: SignalItem[] = [
    {
      ticker: 'AAPL',
      signal: 'LONG',
      exp_return: 0.05,
      confidence: 0.85,
      quality_score: 0.7,
      valuation_score: 0.6,
      momentum_score: 0.8,
      sentiment_score: 0.75,
      composite_score: 0.72,
      risk_adjusted_score: 1.25,
      dt: '2024-01-15',
    },
    {
      ticker: 'MSFT',
      signal: 'SHORT',
      exp_return: -0.03,
      confidence: 0.75,
      quality_score: 0.6,
      valuation_score: 0.5,
      momentum_score: 0.4,
      sentiment_score: 0.55,
      composite_score: 0.52,
      risk_adjusted_score: -0.85,
      dt: '2024-01-15',
    },
  ]

  const mockSetSorting = vi.fn()

  it('renders table with signal data', () => {
    render(
      <BrowserRouter>
        <SignalsTable
          signals={mockSignals}
          sorting={[]}
          onSortingChange={mockSetSorting}
        />
      </BrowserRouter>
    )

    expect(screen.getByText('AAPL')).toBeInTheDocument()
    expect(screen.getByText('MSFT')).toBeInTheDocument()
    expect(screen.getByText('LONG')).toBeInTheDocument()
    expect(screen.getByText('SHORT')).toBeInTheDocument()
  })

  it('renders column headers', () => {
    render(
      <BrowserRouter>
        <SignalsTable
          signals={mockSignals}
          sorting={[]}
          onSortingChange={mockSetSorting}
        />
      </BrowserRouter>
    )

    expect(screen.getByText('Ticker')).toBeInTheDocument()
    expect(screen.getByText('Signal')).toBeInTheDocument()
    expect(screen.getByText('Exp. Return')).toBeInTheDocument()
    expect(screen.getByText('Confidence')).toBeInTheDocument()
  })
})
